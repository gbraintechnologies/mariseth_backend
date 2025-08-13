import base64
from decimal import Decimal

from django.core.files.base import ContentFile
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from apps.accounts.serializers.users import ShortUserSerializer
from apps.farm.models import FarmProduct
from apps.farm.serializers.farm import ShortFarmSerializer
from apps.farm.serializers.products import ShortProductSerializer
from apps.inflow.models import InflowMedia, InflowOrder, InflowOrderHistory, InflowOrderProduct
from apps.inflow.utils import generate_inflow_waybill_id, generate_order_id, generate_serial_number
from apps.warehouse.models import Warehouse, WarehouseProduct, WarehouseProductMovement
from apps.shared.serializers.warehouse import ShortWarehouseSerializer


class ShortInflowOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = InflowOrder
        fields = ('id', 'order_id', 'total_cost', 'status')


class InflowOrderProductSerializer(serializers.ModelSerializer):
    problematic_quantity = serializers.CharField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = InflowOrderProduct
        fields = (
            'id', 'order_id', 'serial_number', 'product', 'farm',
            'quantity', 'unit_price', 'problematic_quantity',
            'reason', 'comment', 'total_cost',
        )
        read_only_fields = ('id', 'serial_number', 'order_id', 'total_cost')


class InflowOrderSerializer(serializers.ModelSerializer):
    products = InflowOrderProductSerializer(many=True)
    destination_warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.filter(is_active=True)
    )

    class Meta:
        model = InflowOrder
        fields = (
            'id', 'aggregator', 'procurement_officer',
            'order_creation_date', 'destination_warehouse',
            'expected_delivery_date', 'status', 'total_bags',
            'additional_costs', 'additional_cost_amount', 'comments',
            'products',
        )
        read_only_fields = ('id', 'order_id', 'total_cost', 'status')

    def create(self, validated_data):
        request = self.context['request']
        products_data = validated_data.pop('products')
        additional_cost = validated_data.get('additional_cost_amount', 0)

        # Generate order ID
        validated_data['order_id'] = generate_order_id(request.organization)
        order = InflowOrder.objects.create(**validated_data)
        order.waybill_id = generate_inflow_waybill_id(order.pk)
        order.save(update_fields=['waybill_id'])

        for product_data in products_data:
            farm_id = product_data['farm'].farm_id
            if not FarmProduct.objects.filter(
                    farm=product_data['farm'],
                    product=product_data['product'],
                    is_active=True
            ).exists():
                raise ValidationError(
                    f"Farm {product_data['farm'].name} does not have this product {product_data['product'].name}")

            product_id = str(product_data['product'].product_id)
            quantity = product_data['quantity']
            product_data['serial_number'] = generate_serial_number(order.id, farm_id, product_id, quantity)
            product_data['total_cost'] = product_data['unit_price'] * product_data['quantity']
            InflowOrderProduct.objects.create(order=order, **product_data)

        # Calculate total_products_cost, total_cost and total_bags for the InflowOrder
        total_products_costs = sum(product.total_cost for product in order.products.all())
        total_bags = sum(product.quantity for product in order.products.all())
        order.total_products_cost = total_products_costs
        order.total_cost = total_products_costs + order.additional_cost_amount
        order.total_bags = total_bags
        order.save(update_fields=['total_products_cost', 'total_cost', 'total_bags'])

        return order

    def update(self, instance, validated_data):
        request = self.context['request']
        products_data = validated_data.pop('products', [])

        # Update InflowOrder instance
        instance.aggregator = validated_data.get('aggregator', instance.aggregator)
        instance.procurement_officer = validated_data.get('procurement_officer', instance.procurement_officer)
        instance.order_creation_date = validated_data.get('order_creation_date', instance.order_creation_date)
        instance.expected_delivery_date = validated_data.get('expected_delivery_date', instance.expected_delivery_date)
        instance.destination_warehouse = validated_data.get('destination_warehouse', instance.destination_warehouse)
        instance.additional_costs = validated_data.get('additional_costs', instance.additional_costs)
        instance.additional_cost_amount = validated_data.get('additional_cost_amount', instance.additional_cost_amount)
        instance.comments = validated_data.get('comments', instance.comments)

        # Calculate total product cost and total cost
        total_products_costs = 0
        total_bag = 0
        for product_data in products_data:
            if 'id' in product_data:
                inflow_order_product = InflowOrderProduct.objects.get(id=product_data['id'], order=instance,
                                                                      is_active=True)
                inflow_order_product.farm = product_data.get('farm', inflow_order_product.farm)
                inflow_order_product.quantity = product_data.get('quantity', inflow_order_product.quantity)
                inflow_order_product.unit_price = product_data.get('unit_price', inflow_order_product.unit_price)
                inflow_order_product.total_cost = inflow_order_product.quantity * inflow_order_product.unit_price
                inflow_order_product.save()
            else:
                if InflowOrderProduct.objects.filter(order=instance, product=product_data['product'],
                                                     farm=product_data['farm']).exists():
                    # Update existing product
                    inflow_order_product = InflowOrderProduct.objects.get(order=instance,
                                                                          product=product_data['product'],
                                                                          farm=product_data['farm'])
                    inflow_order_product.quantity = product_data.get('quantity', inflow_order_product.quantity)
                    inflow_order_product.unit_price = product_data.get('unit_price', inflow_order_product.unit_price)
                    inflow_order_product.total_cost = inflow_order_product.quantity * inflow_order_product.unit_price
                    inflow_order_product.save()
                else:
                    # Create new product
                    product_data['serial_number'] = generate_serial_number(
                                                                           instance.id, product_data['farm'].farm_id,
                                                                           product_data['product'].product_id,
                                                                           product_data['quantity'])
                    product_data['total_cost'] = product_data['unit_price'] * product_data['quantity']
                    if not FarmProduct.objects.filter(farm=product_data['farm'], product=product_data['product'],
                                                      is_active=True).exists():
                        raise ValidationError(
                            f"Farm {product_data['farm'].name} does not have this product {product_data['product'].name}")
                    InflowOrderProduct.objects.create(order=instance, **product_data)

            total_bag += product_data.get('quantity', 0)
            total_products_costs += product_data.get('quantity', 0) * product_data.get('unit_price', 0)

        instance.total_products_cost = total_products_costs
        instance.total_cost = total_products_costs + instance.additional_cost_amount
        instance.total_bags = total_bag
        instance.save()

        return instance


class InflowMediaSerializer(serializers.ModelSerializer):
    class Meta:
        model = InflowMedia
        fields = ('id', 'file', 'name', 'uploaded_at', 'is_complaint')
        read_only_fields = ('id', 'uploaded_at')


class InflowOrderHistorySerializer(serializers.ModelSerializer):
    created_by = ShortUserSerializer()

    class Meta:
        model = InflowOrderHistory
        fields = ('event_type', 'created_by', 'notes',
                  'old_value', 'new_value', 'field_name', 'date_created')
        read_only_fields = fields


class InflowOrderProductAggregateSerializer(serializers.ModelSerializer):
    problematic_quantity = serializers.CharField(required=False, allow_null=True)
    reason = serializers.CharField(required=False, allow_null=True)
    comment = serializers.CharField(required=False, allow_null=True)
    farm = ShortFarmSerializer()
    product = ShortProductSerializer()

    class Meta:
        model = InflowOrderProduct
        fields = (
            'id', 'serial_number', 'product', 'farm',
            'quantity', 'unit_price', 'problematic_quantity',
            'reason', 'comment', 'total_cost'
        )
        read_only_fields = ('id', 'serial_number', 'total_cost')


class FullInflowOrderSerializer(serializers.ModelSerializer):
    aggregator = ShortUserSerializer()
    procurement_officer = ShortUserSerializer()
    destination_warehouse = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()
    media_files = serializers.SerializerMethodField()
    history = InflowOrderHistorySerializer(many=True)

    class Meta:
        model = InflowOrder
        fields = (
            'id', 'aggregator', 'procurement_officer',
            'order_creation_date', 'destination_warehouse',
            'expected_delivery_date', 'actual_delivery_date',
            'status', 'total_bags', 'additional_costs', 'total_products_cost',
            'additional_cost_amount', 'total_cost', 'comments', 'products',
            'media_files', 'history', 'waybill_id'
        )
        read_only_fields = ('id', 'order_id', 'total_cost', 'status', 'total_products_cost')

    def get_products(self, obj):
        return InflowOrderProductAggregateSerializer(
            obj.products.filter(is_active=True),
            many=True
        ).data

    def get_media_files(self, obj):
        return InflowMediaSerializer(
            obj.media_files.filter(is_active=True),
            many=True
        ).data

    def get_destination_warehouse(self, obj):
        if obj.destination_warehouse:
            return {
                "id": obj.destination_warehouse.id,
                "warehouse_id": obj.destination_warehouse.warehouse_id,
                "name": obj.destination_warehouse.name,
                "warehouse_managers": ShortUserSerializer(obj.destination_warehouse.managers, many=True).data
            }
        return None


class DeliveryInspectionApprovalSerializer(serializers.Serializer):
    complaints = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        default=[]
    )
    notes = serializers.CharField(required=False, allow_blank=True)
    images = serializers.ListField(child=serializers.CharField(), required=False, default=[])

    def validate_complaints(self, value):
        for complaint in value:
            if not all(key in complaint for key in ['order_product_id', 'problematic_quantity', 'reason']):
                raise ValidationError("Each complaint must contain order product id, problematic quantity, and reason")
        return value

    def save(self, **kwargs):
        request = self.context['request']
        order = self.instance
        complaints = self.validated_data.get('complaints', [])
        notes = self.validated_data.get('notes', '')
        images = self.validated_data.get('images', [])

        with transaction.atomic():
            # Process complaints
            for complaint in complaints:
                self.process_complaint(order, complaint)

            # Handle images
            for image in images:
                self.process_image(order, image)

            # Update order status
            self.update_order_status(order, notes)

        return order

    def process_complaint(self, order, complaint):
        try:
            product = order.products.get(id=complaint['order_product_id'])

            if complaint['problematic_quantity'] > product.quantity:
                raise ValidationError(
                    f"Problematic quantity exceeds ordered quantity for product {product.id}"
                )

            product.problematic_quantity = complaint['problematic_quantity']
            product.reason = complaint.get('reason', '')
            product.comment = complaint.get('comment', '')
            product.save()

        except InflowOrderProduct.DoesNotExist:
            raise ValidationError(f"Product {complaint['order_product_id']} not found in order")

    def process_image(self, order, image):
        format, imgstr = image.split(';base64,')
        ext = format.split('/')[-1]
        data = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

        InflowMedia.objects.create(
            order=order,
            file=data,
            name=data.name,
            is_complaint=True
        )

    def update_order_status(self, order, notes):
        order.status = 'order_approval'
        order.save()

        InflowOrderHistory.objects.create(
            order=order,
            event_type='status_change',
            created_by=self.context['request'].user,
            old_value='delivery_inspection',
            new_value='order_approval',
            field_name='status',
            notes=notes,
        )


class OrderApprovalSerializer(serializers.Serializer):
    def save(self, **kwargs):
        order = self.instance
        user = self.context['request'].user

        with transaction.atomic():
            self.update_warehouse_stocks(order)
            self.finalize_order(order, user)

        return order

    def update_warehouse_stocks(self, order):
        for order_product in order.products.filter(is_active=True):
            valid_quantity = order_product.quantity - order_product.problematic_quantity
            if valid_quantity <= 0:
                continue

            warehouse_product, created = WarehouseProduct.objects.get_or_create(
                product=order_product.product,
                warehouse=order.destination_warehouse,
                organization=order.organization,
                defaults={'quantity': 0, 'weight': 0}
            )
            warehouse_product.add_stock(order_product.quantity)
            product_weight = order_product.product.weight or Decimal('0.0')
            weight = product_weight * order_product.quantity
            warehouse_product_movement = WarehouseProductMovement.objects.create(
                warehouse=order.destination_warehouse,
                warehouse_product=warehouse_product,
                product=order_product.product,
                quantity=order_product.quantity,
                weight=weight,
                movement_type="inflow",
                amount=Decimal(order_product.total_cost),
                aggregator=order.aggregator,
                procurement_officer=order.procurement_officer,
                record_date=order.order_creation_date,
                inflow_order=order
            )
            order_product.product.add_quantity(order_product.quantity)

    def finalize_order(self, order, user):
        order.status = 'approved'
        order.actual_delivery_date = timezone.now().date()
        order.save()

        InflowOrderHistory.objects.create(
            order=order,
            event_type='status_change',
            created_by=user,
            old_value='order_approval',
            new_value='approved',
            field_name='status',
            notes='Order finalized and warehouse stock updated'
        )
