from django.utils import timezone
from rest_framework import serializers
from django.contrib.auth import get_user_model

from apps.accounts.serializers.users import ShortUserSerializer
from apps.customers.serializers import ShortCustomerSerializer
from apps.farm.serializers.products import FullProductSerializer, ShortProductSerializer
from apps.inflow.serializers import ShortInflowOrderSerializer
from apps.outflow.models import OutflowOrder
from apps.shared.serializers.regions import DistrictSerializer, ShortRegionSerializer
from apps.warehouse.models import Warehouse, WarehouseProduct, WarehouseProductMovement
from apps.warehouse.utils import generate_warehouse_id

User = get_user_model()


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
    managers = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), required=False)

    class Meta:
        model = Warehouse
        fields = (
            'id', 'warehouse_id', 'name', 'region',
            'district', 'capacity', 'managers', 'products'
        )
        read_only_fields = ('id', 'warehouse_id')

    def create(self, validated_data):
        request = self.context['request']
        product_stocks = validated_data.pop('products', [])
        managers_data = validated_data.pop('managers', [])
        validated_data.update({
            'organization': request.organization,
            'warehouse_id': generate_warehouse_id(request.organization.id)
        })
        warehouse = Warehouse.objects.create(**validated_data)
        warehouse.managers.set(managers_data)

        for stock in product_stocks:
            WarehouseProduct.objects.create(
                organization=request.organization,
                warehouse=warehouse,
                **stock
            )

        return warehouse

    def update(self, instance, validated_data):
        managers_data = validated_data.pop('managers', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.date_modified = timezone.now()
        instance.save()

        if managers_data is not None:
            instance.managers.set(managers_data)
        return instance


class FullWarehouseProductSerializer(serializers.ModelSerializer):
    product = FullProductSerializer()

    class Meta:
        model = WarehouseProduct
        fields = ('product', 'weight', 'quantity')


class ProductWarehouseSerializer(serializers.ModelSerializer):
    product = ShortProductSerializer()

    class Meta:
        model = WarehouseProduct
        fields = ('product', 'weight', 'quantity')


class FullWarehouseSerializer(serializers.ModelSerializer):
    # Changed from 'manager' to 'managers' to reflect the ManyToMany relationship.
    # Using ShortUserSerializer with many=True to display multiple managers.
    managers = ShortUserSerializer(many=True)
    region = ShortRegionSerializer()
    district = DistrictSerializer()
    products = ProductWarehouseSerializer(source='product_stocks', many=True)

    class Meta:
        model = Warehouse
        fields = (
            'id', 'warehouse_id', 'name', 'region',
            'district', 'capacity', 'managers', 'date_created',
            'date_modified', 'products'
        )

    def get_managers(self, obj):
        # Returns a list of serialized manager objects using ShortUserSerializer.
        # This provides a more structured representation of managers for the export.
        return ShortUserSerializer(obj.managers.all(), many=True).data


class WarehouseExportSerializer(serializers.ModelSerializer):
    # Changed from 'manager' to 'managers' to reflect the ManyToMany relationship.
    managers = serializers.SerializerMethodField()
    products = serializers.SerializerMethodField()
    date_created = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True, allow_null=True)
    date_modified = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True, allow_null=True)

    class Meta:
        model = Warehouse
        fields = (
            'warehouse_id', 'name', 'region', 'district',
            'capacity', 'managers', 'products',
            'date_created', 'date_modified',
        )

    def get_managers(self, obj):
        # Returns a list of serialized manager objects using ShortUserSerializer.
        # This provides a more structured representation of managers for the export.
        if obj.managers.exists():
            return ", ".join([f"{manager.first_name} {manager.last_name}" for manager in obj.managers.all()])
        return "No Managers"

    def get_products(self, obj):
        product_names = obj.product_stocks.filter(is_active=True).values_list('product__name', flat=True)
        return ", ".join(product_names)


class ManageManagerSerializer(serializers.Serializer):
    manager_id = serializers.IntegerField()
    action = serializers.ChoiceField(choices=[('add', 'Add'), ('remove', 'Remove')])

    def __init__(self, *args, **kwargs):
        self.warehouse = kwargs.pop('warehouse', None)
        self.organization = kwargs.pop('organization', None)
        super().__init__(*args, **kwargs)

    def validate(self, data):
        user_id = data['manager_id']

        # Validate warehouse presence
        if not self.warehouse:
            raise serializers.ValidationError("Warehouse context is required.")

        # Validate user
        try:
            user = User.objects.get(pk=user_id)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found.")

        data['user'] = user
        return data

    def save(self):
        action = self.validated_data['action']
        user = self.validated_data['user']
        warehouse = self.warehouse

        if action == 'add':
            if warehouse.managers.filter(pk=user.pk).exists():
                self.message = "User is already a manager of this warehouse."
            else:
                warehouse.managers.add(user)
                self.message = "Manager added successfully."
                self.updated = True

        elif action == 'remove':
            if not warehouse.managers.filter(pk=user.pk).exists():
                self.message = "User is not a manager of this warehouse."
            else:
                warehouse.managers.remove(user)
                self.message = "Manager removed successfully."
                self.updated = True

        return warehouse


class ShortOutflowOrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = OutflowOrder
        fields = ('id', 'order_id', 'total_cost', 'status')


class WarehouseProductMovementSerializer(serializers.ModelSerializer):
    inflow_order = ShortInflowOrderSerializer(read_only=True)
    outflow_order = ShortOutflowOrderSerializer(read_only=True)
    warehouse = ShortWarehouseSerializer(read_only=True)
    buyer = ShortCustomerSerializer(read_only=True)
    procurement_officer = ShortUserSerializer(read_only=True)
    aggregator = ShortUserSerializer(read_only=True)

    class Meta:
        model = WarehouseProductMovement
        fields = (
            'date_created', 'weight', 'quantity', 'amount',
            'aggregator', 'procurement_officer', 'buyer',
            'warehouse', 'inflow_order', 'outflow_order',
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        order_type = self.context.get('order_type')

        # Include only relevant order field
        if order_type == 'inflow':
            self.fields.pop('outflow_order')
        elif order_type == 'outflow':
            self.fields.pop('inflow_order')

