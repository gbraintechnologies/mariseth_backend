from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.customers.models import Customer
from apps.customers.serializers import CustomerSerializer
from apps.farm.models import Product
from apps.outflow.models import OutflowOrder, OutflowOrderWarehouse, OutflowOrderWarehouseProduct
from apps.outflow.utils import generate_outflow_order_id, generate_serial_number
from apps.warehouse.models import Warehouse, WarehouseProduct

User = get_user_model()


class OutflowOrderProductSerializer(serializers.ModelSerializer):
    product_id = serializers.PrimaryKeyRelatedField(source='product', queryset=Product.objects.filter(is_active=True))
    warehouse_id = serializers.PrimaryKeyRelatedField(source='warehouse',
                                                      queryset=Warehouse.objects.filter(is_active=True))
    price_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = OutflowOrderWarehouseProduct
        fields = ('warehouse_id', 'product_id', 'expected_quantity', 'price_per_unit')

    def validate(self, data):
        warehouse = data['warehouse']
        product = data['product']
        quantity = data['expected_quantity']

        try:
            wp = WarehouseProduct.objects.get(
                product=product,
                warehouse=warehouse,
                is_active=True
            )
            if wp.quantity < quantity:
                raise serializers.ValidationError(
                    f"Insufficient stock for product {product.name} in warehouse "
                    f"{warehouse.name}. Available: {wp.quantity}"
                )
        except WarehouseProduct.DoesNotExist:
            raise serializers.ValidationError(
                f"Product {product} not available in warehouse {warehouse}"
            )

        data['available_quantity'] = wp.quantity
        data['cost'] = quantity * data['price_per_unit']
        return data


class OutflowOrderSerializer(serializers.ModelSerializer):
    products = OutflowOrderProductSerializer(many=True, source='warehouse_products', allow_null=True)
    customer = serializers.PrimaryKeyRelatedField(queryset=Customer.objects.filter(is_active=True))
    procurement_officer = serializers.PrimaryKeyRelatedField(queryset=User.objects.filter(is_active=True),
                                                             allow_null=True)

    class Meta:
        model = OutflowOrder
        fields = (
            'customer', 'procurement_officer', 'destination',
            'expected_delivery_date', 'products', 'total_quantity',
            'total_cost', 'extra_comments'
        )
        read_only_fields = ('total_quantity', 'total_cost', 'order_id')

    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        products_data = validated_data.pop('warehouse_products')
        validated_data["organization"] = request.organization
        validated_data["created_by"] = request.user
        validated_data["order_id"] = generate_outflow_order_id(request.organization.id)
        order = OutflowOrder.objects.create(**validated_data)

        total_quantity = 0
        total_cost = 0

        # Group products by warehouse
        for product_data in products_data:
            warehouse = product_data['warehouse']
            outflow_order_warehouse, _ = OutflowOrderWarehouse.objects.get_or_create(
                outflow_order=order,
                warehouse=warehouse
            )
            product = product_data['product']
            serial_number = generate_serial_number(
                warehouse.warehouse_id,
                product.name,
                product_data['expected_quantity']
            )

            OutflowOrderWarehouseProduct.objects.create(
                serial_number=serial_number,
                outflow_order_warehouse=outflow_order_warehouse,
                product=product,
                expected_quantity=product_data['expected_quantity'],
                price_per_unit=product_data['price_per_unit'],
                cost=product_data['cost']
            )

            total_quantity += product_data['expected_quantity']
            total_cost += product_data['cost']

        order.total_quantity = total_quantity
        order.total_cost = total_cost
        order.save()
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        # 1) Update scalar fields
        for attr in ('destination', 'expected_delivery_date', 'extra_comments'):
            if attr in validated_data:
                setattr(instance, attr, validated_data[attr])
        instance.save()

        # 2) Sync products if provided
        incoming = validated_data.get('warehouse_products')
        if incoming is not None:
            # Track which warehouse-product combinations to keep (using original warehouse IDs)
            keep = set()
            warehouse_mapping = {}  # Maps warehouse IDs to OutflowOrderWarehouse instances

            for item in incoming:
                wh_id = item['warehouse'].id  # Original warehouse ID
                prod_id = item['product'].id
                qty = int(item['expected_quantity'])
                price = Decimal(str(item['price_per_unit']))
                cost = qty * price

                # Get or create warehouse group using original warehouse ID
                if wh_id not in warehouse_mapping:
                    warehouse_mapping[wh_id] = OutflowOrderWarehouse.objects.get_or_create(
                        outflow_order=instance,
                        warehouse_id=wh_id
                    )[0]

                wh_group = warehouse_mapping[wh_id]

                # Get or create product line
                line, created = OutflowOrderWarehouseProduct.objects.update_or_create(
                    outflow_order_warehouse=wh_group,
                    product_id=prod_id,
                    defaults={
                        'expected_quantity': qty,
                        'price_per_unit': price,
                        'cost': cost,
                        'serial_number': generate_serial_number(
                            wh_group.warehouse.warehouse_id,
                            item['product'].name,
                            qty
                        )
                    }
                )

                # Clamp available to actual stock
                stock = WarehouseProduct.objects.get(
                    warehouse_id=wh_id,
                    product_id=prod_id,
                    is_active=True
                ).quantity
                line.available_quantity = min(qty, stock)
                line.save()

                keep.add((wh_id, prod_id))  # Track by original warehouse ID and product ID

            # Delete only products not present in update data
            for existing_wh in instance.warehouses.all():
                for existing_product in existing_wh.products.all():
                    key = (existing_wh.warehouse.id, existing_product.product.id)
                    if key not in keep:
                        existing_product.delete()

        # 3) Remove empty warehouse groups
        instance.warehouses.filter(products__isnull=True).delete()

        # 4) Recalculate totals (same as before)
        total_qty = 0
        total_cost = Decimal('0.00')
        for wh_group in instance.warehouses.all():
            for line in wh_group.products.filter(is_active=True):
                total_qty += line.expected_quantity
                total_cost += line.cost

        instance.total_quantity = total_qty
        instance.total_cost = total_cost
        instance.amount_due = total_cost - instance.amount_paid
        instance.save()

        return instance


class OutflowWarehouseProductSerializer(serializers.ModelSerializer):
    product_id = serializers.IntegerField(source='product.id')
    product_name = serializers.CharField(source='product.name')
    price_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2)
    cost = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = OutflowOrderWarehouseProduct
        fields = (
            'id', 'serial_number', 'product_id', 'product_name',
            'expected_quantity', 'price_per_unit', 'cost', 'status'
        )


class OutflowOrderWarehouseSerializer(serializers.ModelSerializer):
    products = OutflowWarehouseProductSerializer(
        many=True,
        source='products.all'
    )
    total_quantity = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    name = serializers.CharField(source='warehouse.name')

    class Meta:
        model = OutflowOrderWarehouse
        fields = ('id', 'name', 'products', 'status', 'total_quantity', 'total_cost')

    def get_total_quantity(self, obj):
        return sum(p.expected_quantity for p in obj.products.filter(is_active=True))

    def get_total_cost(self, obj):
        return sum(float(p.cost) for p in obj.products.filter(is_active=True))


class FullOutflowOrderSerializer(serializers.ModelSerializer):
    warehouses = OutflowOrderWarehouseSerializer(
        many=True,
        source='warehouses.all'
    )
    customer = CustomerSerializer()
    procurement_officer = ShortUserSerializer()
    total_quantity = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=2)

    class Meta:
        model = OutflowOrder
        fields = (
            'id', 'order_id', 'customer', 'procurement_officer',
            'destination', 'expected_delivery_date', 'status',
            'total_quantity', 'total_cost', 'warehouses'
        )
        read_only_fields = fields

    def to_representation(self, instance):
        representation = super().to_representation(instance)

        # Sort warehouses by ID for consistent output
        representation['warehouses'] = sorted(
            representation['warehouses'],
            key=lambda x: x['id']
        )
        return representation

# class OutflowOrderUpdateRequestSerializer(serializers.ModelSerializer):
#     # similar to create but partial, allow changing warehouses
#     class Meta:
#         model = OutflowOrder
#         fields = ('destination', 'expected_delivery_date', 'extra_comments')
#
#
# class OutflowOrderDeliveryInfoRequestSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = OutflowOrderDeliveryInformation
#         exclude = ('outflow_order',)
#
#     def validate(self, attrs):
#         order = self.context['order']
#         if order.status != OutflowOrder.STATUS_CHOICES[1][0]:  # 'truck_pickup'
#             raise serializers.ValidationError("Can only assign delivery info at truck_pickup stage.")
#         return attrs
#
#     @transaction.atomic
#     def create(self, validated_data):
#         order = self.context['order']
#         validated_data['outflow_order'] = order
#         di = super().create(validated_data)
#         # send_notification(
#         #     recipients=[m.user for m in order.warehouses.all()],
#         #     message=f"Delivery info assigned for order {order.outflow_order_id}"
#         # )
#         order.history.create(field_name='status', old_value=order.status, new_value=order.status)
#         return di
#
#
# class OutflowOrderPaymentRequestSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = OutflowOrderPayments
#         exclude = ('outflow_order', 'payment_date')
#
#     def save(self, **kwargs):
#         order = self.context['order']
#         payment = super().save(outflow_order=order, **kwargs)
#         # update order amounts
#         order.amount_paid += payment.amount_paid
#         order.amount_due = order.total_cost - order.amount_paid
#         if order.amount_due <= 0:
#             order.status = OutflowOrder.STATUS_CHOICES[5][0]  # 'full_payment'
#         else:
#             order.status = OutflowOrder.STATUS_CHOICES[4][0]  # 'partial_payment'
#         order.save()
#         return payment
#
#
# #
# # —————————————— RESPONSE SERIALIZERS ——————————————
# #
#
# class OutflowOrderWarehouseProductResponseSerializer(serializers.ModelSerializer):
#     product = ProductSerializer(read_only=True)
#
#     class Meta:
#         model = OutflowOrderWarehouseProduct
#         fields = ('id', 'product', 'expected_quantity', 'available_quantity', 'price_per_unit', 'cost', 'status')
#
#
# class OutflowOrderWarehouseResponseSerializer(serializers.ModelSerializer):
#     warehouse = WarehouseSerializer(read_only=True)
#     products = OutflowOrderWarehouseProductResponseSerializer(many=True, read_only=True)
#
#     class Meta:
#         model = OutflowOrderWarehouse
#         fields = ('id', 'warehouse', 'total_quantity', 'total_cost', 'status', 'products')
#
#
# class OutflowOrderDeliveryInfoResponseSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = OutflowOrderDeliveryInformation
#         exclude = ('outflow_order',)
#
#
# class OutflowOrderPaymentResponseSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = OutflowOrderPayments
#         exclude = ('outflow_order',)
#
#
# class OutflowOrderResponseSerializer(serializers.ModelSerializer):
#     warehouses = OutflowOrderWarehouseResponseSerializer(many=True)
#     delivery_information = OutflowOrderDeliveryInfoResponseSerializer(many=True)
#     payments = OutflowOrderPaymentResponseSerializer(many=True)
#
#     class Meta:
#         model = OutflowOrder
#         fields = (
#             'id', 'outflow_order_id', 'status', 'customer', 'destination',
#             'expected_delivery_date', 'actual_delivery_date', 'total_quantity',
#             'total_cost', 'amount_paid', 'amount_due', 'extra_comments',
#             'warehouses', 'delivery_information', 'payments',
#         )
