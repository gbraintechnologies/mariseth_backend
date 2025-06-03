from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.customers.serializers import CustomerSerializer
from apps.outflow.models import OutflowOrder, OutflowOrderWarehouse, OutflowOrderWarehouseProduct


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
        fields = ('id', 'name','status', 'total_quantity', 'total_cost', 'products', )

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
        if not request:
            return []

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


# serializers.py
import base64
from django.core.files.base import ContentFile
from rest_framework import serializers
from apps.outflow.models import OutflowOrderWarehouse, OutflowOrderWarehouseProduct, OutflowOrderWarehouseImages


class Base64ImageField(serializers.ImageField):
    def to_internal_value(self, data):
        if isinstance(data, str) and data.startswith('data:image'):
            format, imgstr = data.split(';base64,')
            ext = format.split('/')[-1]
            data = ContentFile(base64.b64decode(imgstr), name=f'verification.{ext}')
        return super().to_internal_value(data)


class ProductVerificationSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutflowOrderWarehouseProduct
        fields = ['id', 'available_quantity', 'reason', 'comments']

    def validate_available_quantity(self, value):
        if value < 0:
            raise serializers.ValidationError("Quantity cannot be negative")
        return value


class WarehouseVerificationSerializer(serializers.ModelSerializer):
    products = ProductVerificationSerializer(many=True)
    images = Base64ImageField(required=False, allow_null=True, many=True)

    class Meta:
        model = OutflowOrderWarehouse
        fields = ['id', 'products', 'images']

    def update(self, instance, validated_data):
        products_data = validated_data.pop('products', [])
        images_data = validated_data.pop('images', [])

        # Determine verification mode
        has_complaint = any(
            p.get('available_quantity') != instance.products.get(id=p['id']).expected_quantity or
            p.get('reason') or p.get('comments')
            for p in products_data
        )

        with transaction.atomic():
            # Process products
            all_verified = True
            for product_data in products_data:
                product = instance.products.get(id=product_data['id'])

                # Auto-verification: Set to expected quantity if no complaint
                if not has_complaint:
                    product_data['available_quantity'] = product.expected_quantity
                    product_data['reason'] = ''
                    product_data['comments'] = ''

                # Update product
                for attr, value in product_data.items():
                    setattr(product, attr, value)

                # Set status based on quantity comparison
                if product.available_quantity >= product.expected_quantity:
                    product.status = 'verified'
                else:
                    product.status = 'not_enough_stock'
                    all_verified = False

                product.save()

            # Update warehouse status
            instance.status = 'verified' if all_verified else 'not_enough_stock'
            instance.save()

            # Save images
            for image in images_data:
                OutflowOrderWarehouseImages.objects.create(
                    outflow_order_warehouse=instance,
                    image=image
                )

            # Return context for view to handle notifications
            return {
                'warehouse': instance,
                'all_verified': all_verified,
                'has_complaint': has_complaint
            }