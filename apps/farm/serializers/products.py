
from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.farm.models import Product
from apps.farm.utils import generate_product_id
from apps.shared.models import CustomType
from apps.shared.serializers.custom_types import CustomTypeSerializer


class ShortProductSerializer(serializers.ModelSerializer):
    class Meta:
        model = Product
        fields = ('id', 'product_id', 'name', 'type', 'status', 'color')
        read_only_fields = ('id',)


class ProductSerializer(serializers.ModelSerializer):
    category = serializers.PrimaryKeyRelatedField(
        queryset=CustomType.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )

    class Meta:
        model = Product
        fields = (
            'id', 'name', 'category', 'weight', 'weight_metric',
            'quantity', 'quantity_metric', 'type', 'season_status',
            'status', 'season_start', 'season_end', 'description',
            'breed', 'color',
        )
        read_only_fields = ('id',)

    def validate(self, data):
        if data.get('season_start') and data.get('season_end'):
            if data['season_start'] > data['season_end']:
                raise serializers.ValidationError(
                    {'season_end': 'Season end date must be after start date'}
                )
        if data.get('type') == 'livestock' and not data.get('breed'):
            raise serializers.ValidationError(
                {'breed': 'Breed is required for livestock'}
            )

        return data

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['organization'] = self.context['request'].organization
        product = Product.objects.create(**validated_data)
        product.product_id = generate_product_id(product.name)
        product.save()

        # --- Trigger Manager.io Integration ---
        from apps.shared.models import IntegrationLog
        from apps.shared.tasks.manager_tasks import sync_inventory_item_to_manager

        if not IntegrationLog.objects.filter(object_id=product.id, content_type__model='product').exists():
            log = IntegrationLog.objects.create(content_object=product, created_by=self.context['request'].user)
            sync_inventory_item_to_manager.delay(log.id)
        # --- End Integration Trigger ---

        return product

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = self.context['request'].user
        instance.save()
        return instance


class FullProductSerializer(serializers.ModelSerializer):
    created_by = ShortUserSerializer()
    category = CustomTypeSerializer()
    weight_metric = CustomTypeSerializer()
    quantity_metric = CustomTypeSerializer()

    class Meta:
        model = Product
        fields = (
            'id', 'product_id', 'name', 'category', 'weight', 'weight_metric',
            'quantity', 'quantity_metric', 'type', 'season_status', 'status',
            'season_start', 'season_end', 'description', 'breed', 'color',
            'created_by', 'date_created', 'last_updated'
        )
        read_only_fields = ('id', 'created_by', 'date_created', 'last_updated')


class ProductExportSerializer(serializers.ModelSerializer):
    category = serializers.StringRelatedField()
    weight_metric = serializers.StringRelatedField()
    quantity_metric = serializers.StringRelatedField()
    type = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()
    season_status = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    date_created = serializers.DateTimeField(format="%d-%m-%Y", allow_null=True)
    last_updated = serializers.DateField(format="%d-%m-%Y", allow_null=True)
    season_start = serializers.DateField(format="%d-%m-%Y", allow_null=True)
    season_end = serializers.DateField(format="%d-%m-%Y", allow_null=True)

    class Meta:
        model = Product
        fields = (
            'product_id', 'name', 'type', 'category', 'weight', 'weight_metric',
            'quantity', 'quantity_metric', 'season_status', 'status', 'season_start',
            'season_end', 'description', 'breed', 'created_by', 'date_created', 'last_updated'
        )

    def get_type(self, obj):
        return dict(Product.PRODUCT_TYPE_CHOICES).get(obj.type, "")

    def get_status(self, obj):
        return dict(Product.PRODUCT_STATUS_CHOICES).get(obj.status, "")

    def get_season_status(self, obj):
        return dict(Product.PRODUCT_SEASON_CHOICES).get(obj.season_status, "")

    def get_created_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else ""
