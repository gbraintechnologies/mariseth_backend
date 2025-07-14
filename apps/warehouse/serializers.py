from django.utils import timezone
from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.farm.serializers.products import FullProductSerializer
from apps.inflow.serializers import ShortInflowOrderSerializer
from apps.outflow.models import OutflowOrder
from apps.shared.serializers.regions import DistrictSerializer, ShortRegionSerializer
from apps.warehouse.models import Warehouse, WarehouseProduct, WarehouseProductMovement
from apps.warehouse.utils import generate_warehouse_id


class ShortWarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ('id', 'warehouse_id', 'name')


class WarehouseProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = WarehouseProduct
        fields = ('product', 'weight', 'quantity')


class WarehouseSerializer(serializers.ModelSerializer):
    products = WarehouseProductSerializer(many=True, required=False)

    class Meta:
        model = Warehouse
        fields = (
            'id', 'warehouse_id', 'name', 'region',
            'district', 'capacity', 'manager', 'products'
        )
        read_only_fields = ('id', 'warehouse_id')

    def create(self, validated_data):
        request = self.context['request']
        product_stocks = validated_data.pop('products', [])
        validated_data.update({
            'organization': request.organization,
            'warehouse_id': generate_warehouse_id(request.organization.id)
        })
        warehouse = Warehouse.objects.create(**validated_data)

        for stock in product_stocks:
            WarehouseProduct.objects.create(
                organization=request.organization,
                warehouse=warehouse,
                **stock
            )

        return warehouse

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.date_modified = timezone.now()
        instance.save()
        return instance


class FullWarehouseProductSerializer(serializers.ModelSerializer):
    product = FullProductSerializer()

    class Meta:
        model = WarehouseProduct
        fields = ('product', 'weight', 'quantity')


class FullWarehouseSerializer(serializers.ModelSerializer):
    manager = ShortUserSerializer()
    products = serializers.SerializerMethodField()
    region = ShortRegionSerializer()
    district = DistrictSerializer()

    class Meta:
        model = Warehouse
        fields = (
            'id', 'warehouse_id', 'name', 'region',
            'district', 'capacity', 'manager', 'date_created',
            'date_modified'
        )


class WarehouseExportSerializer(serializers.ModelSerializer):
    manager = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()
    date_created = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True, allow_null=True)
    date_modified = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True, allow_null=True)

    class Meta:
        model = Warehouse
        fields = (
            'warehouse_id', 'name', 'region', 'district',
            'capacity', 'manager', 'products',
            'date_created', 'date_modified',
        )

    def get_manager(self, obj):
        if obj.manager:
            return f"{obj.manager.first_name} {obj.manager.last_name}"
        return "No Manager"

    def get_products(self, obj):
        product_names = obj.product_stocks.filter(is_active=True).values_list('product__name', flat=True)
        return ", ".join(product_names)


class ShortOutflowOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutflowOrder
        fields = ('id', 'order_id', 'total_cost', 'status')


class WarehouseProductMovementSerializer(serializers.ModelSerializer):
    inflow_order = ShortInflowOrderSerializer(read_only=True)
    outflow_order = ShortOutflowOrderSerializer(read_only=True)

    class Meta:
        model = WarehouseProductMovement
        fields = (
            'date_created', 'weight', 'quantity', 'amount',
            'procurement_officer', 'inflow_order', 'outflow_order',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        order_type = self.context.get('order_type')

        # Include only relevant order field
        if order_type == 'inflow':
            self.fields.pop('outflow_order')
        elif order_type == 'outflow':
            self.fields.pop('inflow_order')

