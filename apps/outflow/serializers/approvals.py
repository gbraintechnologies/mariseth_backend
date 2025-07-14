from decimal import Decimal

import sentry_sdk
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.customers.serializers import CustomerSerializer
from apps.farm.serializers.products import ShortProductSerializer
from apps.outflow.models import OutflowOrder, OutflowOrderDeliveryInformationWarehouse, OutflowOrderWarehouse, \
    OutflowOrderWarehouseHistory, OutflowOrderWarehouseImages, OutflowOrderWarehouseProduct
from apps.outflow.serializers.outflow import OutflowOrderDeliveryInfoResponseSerializer
from apps.shared.utils.helpers import base64_to_image
from apps.warehouse.models import WarehouseProduct, WarehouseProductMovement
from apps.warehouse.serializers import ShortWarehouseSerializer


class OutflowWarehouseImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutflowOrderWarehouseImages
        fields = ('id', 'image', 'date_created')


class OutflowWarehouseProductSerializer(serializers.ModelSerializer):
    product = ShortProductSerializer(read_only=True)
    price_per_unit = serializers.DecimalField(max_digits=10, decimal_places=2)
    cost = serializers.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        model = OutflowOrderWarehouseProduct
        fields = (
            'id', 'serial_number', 'available_quantity',
            'expected_quantity', 'price_per_unit', 'cost',
            'status', 'product', 'reason', 'comments'
        )


class OutflowOrderWarehouseSerializer(serializers.ModelSerializer):
    products = OutflowWarehouseProductSerializer(
        many=True,
        source='products.all'
    )
    total_quantity = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    warehouse = ShortWarehouseSerializer()
    images = OutflowWarehouseImageSerializer(many=True, source='images.all', read_only=True)
    delivery_information = serializers.SerializerMethodField()

    class Meta:
        model = OutflowOrderWarehouse
        fields = (
            'id', 'status', 'total_quantity', 'total_cost',
            'warehouse', 'products', 'images', 'delivery_information'
        )

    def get_delivery_information(self, obj):
        if not obj:
            return None
        links = OutflowOrderDeliveryInformationWarehouse.objects.select_related(
            'outflow_order_delivery_information'
        ).filter(
            outflow_order_delivery_information__outflow_order=obj.outflow_order,
            warehouse=obj.warehouse
        )
        delivery_infos = [link.outflow_order_delivery_information for link in links]
        return OutflowOrderDeliveryInfoResponseSerializer(delivery_infos, many=True).data

    def get_total_quantity(self, obj):
        return sum(p.expected_quantity for p in obj.products.filter(is_active=True))

    def get_total_cost(self, obj):
        return sum(float(p.cost) for p in obj.products.filter(is_active=True))


class OutflowOrderApprovalSerializer(serializers.ModelSerializer):
    warehouses = serializers.SerializerMethodField()
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

    def get_warehouses(self, obj):
        request = self.context.get('request')
        # Only include warehouses in this order that are managed by the user
        managed = obj.warehouses.select_related('warehouse').filter(
            warehouse__manager=request.user
        )
        return OutflowOrderWarehouseSerializer(managed, many=True).data

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        representation['warehouses'] = sorted(
            representation['warehouses'],
            key=lambda x: x['id']
        )
        return representation


class ProductVerificationSerializer(serializers.ModelSerializer):
    id = serializers.IntegerField(read_only=False, required=True)

    class Meta:
        model = OutflowOrderWarehouseProduct
        fields = ('id', 'available_quantity', 'reason', 'comments')

    def validate_available_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative")
        return value


class WarehouseVerificationSerializer(serializers.ModelSerializer):
    products = ProductVerificationSerializer(many=True, required=False, default=[])
    images = serializers.ListField(child=serializers.CharField(), required=False, default=[])

    class Meta:
        model = OutflowOrderWarehouse
        fields = ['id', 'products', 'images']

    def update(self, instance, validated_data):
        request = self.context.get('request')
        products_data = validated_data.get('products', [])
        images_data = validated_data.pop('images', [])

        with transaction.atomic():
            all_verified = True
            old_warehouse_status = instance.status

            # Case 1: No product data sent (Auto-verification scenario)
            if not products_data:
                for product in instance.products.all():
                    # Get actual stock from warehouse
                    try:
                        warehouse_product = WarehouseProduct.objects.get(
                            warehouse=instance.warehouse,
                            product=product.product
                        )
                        actual_stock = warehouse_product.quantity or 0
                    except WarehouseProduct.DoesNotExist:
                        actual_stock = 0

                    # Auto-verify: Set available_quantity to actual stock
                    product.available_quantity = actual_stock
                    product.reason = None
                    product.comments = None

                    # Set status based on stock availability
                    if actual_stock >= product.expected_quantity:
                        product.status = 'verified'
                    else:
                        product.status = 'not_enough_stock'
                        all_verified = False

                    product.save()

            # Case 2: Product data sent (Manual verification with complaints/adjustments)
            else:
                for product_data in products_data:
                    try:
                        product = instance.products.get(id=product_data['id'])
                    except OutflowOrderWarehouseProduct.DoesNotExist:
                        raise serializers.ValidationError(
                            f"Product with ID {product_data['id']} not found in this warehouse order."
                        )

                    # Update product fields from the payload
                    for attr, value in product_data.items():
                        if hasattr(product, attr) and attr != 'id':
                            setattr(product, attr, value)

                    # Set status based on quantity comparison
                    if product.available_quantity >= product.expected_quantity:
                        product.status = 'verified'
                    else:
                        product.status = 'not_enough_stock'
                        all_verified = False

                    product.save()

            # Update warehouse order status
            instance.status = 'verified' if all_verified else 'not_enough_stock'
            instance.save()
            if old_warehouse_status != instance.status:
                OutflowOrderWarehouseHistory.objects.create(
                    outflow_order_warehouse=instance,
                    field='status',
                    old_value=old_warehouse_status,
                    new_value=instance.status,
                    created_by=request.user
                )

            # Save images if provided
            if images_data is not None:
                for image_data in images_data:
                    OutflowOrderWarehouseImages.objects.create(
                        outflow_order_warehouse=instance,
                        image=base64_to_image(image_data)
                    )

            # Update the main order status
            order = instance.outflow_order
            order.mark_as_availability_checked_if_all_verified(verified_warehouse=instance, user=request.user)

        return order


class MarkOrderPickedSerializer(serializers.Serializer):
    pick_up = serializers.BooleanField(default=True)
    pick_up_datetime = serializers.DateTimeField(required=False)

    def validate(self, data):
        if data.get("pick_up") and not data.get("pick_up_datetime"):
            data["pick_up_datetime"] = timezone.now()
        return data

    def update_warehouse_stocks_outflow(self, order, outflow_warehouse):
        """
        Reduce stock and create movement records for the specific warehouse
        when goods leave (order_pickup).
        """
        with transaction.atomic():
            for warehouse_product_order in outflow_warehouse.products.filter(status='verified'):
                try:
                    warehouse_product = WarehouseProduct.objects.get(
                        product=warehouse_product_order.product,
                        warehouse=outflow_warehouse.warehouse,
                        organization=order.organization
                    )
                    # 1) remove stock
                    warehouse_product.remove_stock(warehouse_product_order.expected_quantity)
                    # 2) record movement
                    warehouse_product_movement = WarehouseProductMovement.objects.create(
                        warehouse=outflow_warehouse.warehouse,
                        warehouse_product=warehouse_product,
                        product=warehouse_product_order.product,
                        quantity=Decimal(warehouse_product_order.expected_quantity),
                        weight=warehouse_product_order.product.weight * warehouse_product_order.expected_quantity,
                        movement_type="outflow",
                        amount=warehouse_product_order.cost,
                        buyer=order.customer,
                        procurement_officer=order.procurement_officer,
                        record_date=timezone.now().date(),
                        outflow_order=order,
                    )
                    # 3) update global product quantity
                    warehouse_product_order.product.remove_quantity(
                        warehouse_product_order.expected_quantity
                    )

                except WarehouseProduct.DoesNotExist:
                    print(
                        f"Product {warehouse_product_order.product.name} not found in warehouse {outflow_warehouse.warehouse.name} -  {outflow_warehouse.warehouse.warehouse_id}")
                    continue
                except Exception as e:
                    sentry_sdk.capture_exception(e)
                    continue

    def update(self, order, validated_data):
        request = self.context["request"]
        outflow_warehouse = self.context["outflow_warehouse"]

        if outflow_warehouse.status == "not_enough_stock" or outflow_warehouse.status == "pending_verification":
            raise serializers.ValidationError("Warehouse has not been verified yet.")

        if outflow_warehouse.status == "order_pickup":
            raise serializers.ValidationError("Warehouse has already been marked as picked up.")

        # Get ALL delivery links for this warehouse-order combination
        delivery_links = OutflowOrderDeliveryInformationWarehouse.objects.filter(
            outflow_order_delivery_information__outflow_order=order,
            warehouse=outflow_warehouse.warehouse
        )

        if not delivery_links.exists():
            raise serializers.ValidationError("Delivery Information not found for this warehouse.")

        # Update all found delivery links
        for link in delivery_links:
            link.pick_up = validated_data.get("pick_up", True)
            link.pick_up_datetime = validated_data.get("pick_up_datetime") or timezone.now()
            link.save()

        # Update warehouse status only once
        old_warehouse_status = outflow_warehouse.status
        outflow_warehouse.status = "order_pickup"
        outflow_warehouse.save()

        # Create history only if status actually changed
        if old_warehouse_status != outflow_warehouse.status:
            OutflowOrderWarehouseHistory.objects.create(
                outflow_order_warehouse=outflow_warehouse,
                field='status',
                old_value=old_warehouse_status,
                new_value=outflow_warehouse.status,
                created_by=request.user
            )
        # ─── stock leaves the warehouse now ───
        self.update_warehouse_stocks_outflow(order, outflow_warehouse)

        # — finally update overall order status if all warehouses are picked up —
        order.update_status_to_truck_pickup_if_ready(
            picked_warehouse=outflow_warehouse,
            user=request.user
        )

        return order


class ShortOutflowOrderWarehouseSerializer(serializers.ModelSerializer):
    products = OutflowWarehouseProductSerializer(
        many=True,
        source='products.all'
    )
    total_quantity = serializers.SerializerMethodField()
    total_cost = serializers.SerializerMethodField()
    warehouse = ShortWarehouseSerializer()

    class Meta:
        model = OutflowOrderWarehouse
        fields = (
            'id', 'status', 'total_quantity', 'total_cost',
            'warehouse', 'products')

    def get_total_quantity(self, obj):
        return sum(p.expected_quantity for p in obj.products.filter(is_active=True))

    def get_total_cost(self, obj):
        return sum(float(p.cost) for p in obj.products.filter(is_active=True))


class OutflowWarehouseListSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='outflow_order.id')
    order_id = serializers.CharField(source='outflow_order.order_id')
    date_created = serializers.DateTimeField(source='outflow_order.date_created')
    customer = serializers.CharField(source='outflow_order.customer.name')
    procurement_officer = serializers.CharField(source='outflow_order.procurement_officer.get_full_name')
    warehouse = serializers.SerializerMethodField()

    def get_warehouse(self, obj):
        return ShortOutflowOrderWarehouseSerializer(obj).data


class OutflowWarehouseOrderDetailSerializer(serializers.Serializer):
    id = serializers.IntegerField(source='outflow_order.id')
    order_id = serializers.CharField(source='outflow_order.order_id')
    status = serializers.CharField(source='outflow_order.status')
    destination = serializers.CharField(source='outflow_order.destination')
    expected_delivery_date = serializers.DateField(source='outflow_order.expected_delivery_date')
    actual_delivery_date = serializers.DateField(source='outflow_order.actual_delivery_date')
    date_created = serializers.DateTimeField(source='outflow_order.date_created')
    total_quantity = serializers.IntegerField(source='outflow_order.total_quantity')
    additional_cost = serializers.CharField(source='outflow_order.additional_costs')
    additional_cost_amount = serializers.DecimalField(max_digits=12, decimal_places=2,
                                                      source='outflow_order.additional_cost_amount')
    extra_comments = serializers.CharField(source='outflow_order.extra_comments')
    customer = CustomerSerializer(source='outflow_order.customer')
    procurement_officer = ShortUserSerializer(source='outflow_order.procurement_officer')
    warehouse = serializers.SerializerMethodField()

    def get_warehouse(self, obj):
        return OutflowOrderWarehouseSerializer(obj).data
