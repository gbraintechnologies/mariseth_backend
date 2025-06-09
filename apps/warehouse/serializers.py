from rest_framework import serializers
from django.utils import timezone
from apps.accounts.serializers.users import ShortUserSerializer
from apps.shared.serializers.regions import DistrictSerializer, ShortRegionSerializer
from apps.warehouse.models import Warehouse, WarehouseProduct
from apps.warehouse.utils import generate_warehouse_id


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
            'date_modified', 'products'
        )

    def get_products(self, obj):
        return WarehouseProductSerializer(
            obj.product_stocks.filter(is_active=True),
            many=True
        ).data


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

