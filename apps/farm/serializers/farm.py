from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.farm.models import Farm, FarmProduct, Product
from apps.farm.utils import generate_farm_id


class ShortFarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = ('id', 'name', 'farm_id', 'land_ownership')


class FarmProductSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.all())

    class Meta:
        model = FarmProduct
        fields = ('id', 'product', 'is_main_product', 'notes')
        read_only_fields = ('id',)


class FarmSerializer(serializers.ModelSerializer):
    products = FarmProductSerializer(many=True)

    class Meta:
        model = Farm
        fields = (
            'id', 'farm_type', 'type', 'name', 'location', 'district',
            'size', 'size_metric', 'livestock_kept', 'has_access_to_market',
            'irrigation', 'use_of_fertilizers', 'farming_methods', 'provide_training',
            'government_ngo_support', 'specify_support', 'areas_of_assistance',
            'land_ownership', 'other_specification', 'products'
        )
        read_only_fields = ('id',)

    def validate(self, data):
        for field in data.keys():
            if field not in self.Meta.fields:
                raise serializers.ValidationError({field: "Invalid field."})
        return data

    def create(self, validated_data):
        request = self.context['request']
        validated_data['created_by'] = request.user
        validated_data['organization'] = request.organization
        validated_data['farm_id'] = generate_farm_id(validated_data['name'])
        farm_products_data = validated_data.pop('products')
        farm = Farm.objects.create(**validated_data)
        for farm_product_data in farm_products_data:
            FarmProduct.objects.create(farm=farm, **farm_product_data)
        return farm

    def update(self, instance, validated_data):
        # TODO: ADD SIGNALS TO LOG CHANGES
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = self.context['request'].user
        instance.save()
        return instance


class FullFarmSerializer(serializers.ModelSerializer):
    created_by = ShortUserSerializer()
    products = serializers.SerializerMethodField()

    class Meta:
        model = Farm
        fields = (
            'id', 'farm_id', 'farm_type', 'type', 'name', 'location', 'district',
            'size', 'size_metric', 'livestock_kept', 'has_access_to_market',
            'irrigation', 'use_of_fertilizers', 'farming_methods', 'provide_training',
            'government_ngo_support', 'specify_support', 'areas_of_assistance',
            'land_ownership', 'other_specification', 'created_by', 'date_created',
            'products'
        )
        read_only_fields = ('id', 'created_by', 'updated_by', 'date_created')

    def get_products(self, obj):
        return FarmProductSerializer(obj.farmproduct_set.filter(is_active=True), many=True).data


class FarmDeleteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = []

    def validate(self, attrs):
        farm = self.instance
        if farm.farmers.filter(is_active=True).exists():
            raise serializers.ValidationError(
                "Cannot delete farm with active farmers. Please move them to another farm first."
            )
        return attrs


class FarmProductDeleteSerializer(serializers.Serializer):
    farm_product_ids = serializers.ListField(
        child=serializers.IntegerField(),
        min_length=1,
        max_length=100
    )

    def validate_farm_product_ids(self, value):
        farm = self.context['farm']

        existing_products = FarmProduct.objects.filter(
            id__in=value,
            farm=farm,
            is_active=True
        ).values_list('id', flat=True)

        # Check for invalid IDs
        invalid_ids = set(value) - set(existing_products)
        if invalid_ids:
            raise serializers.ValidationError(
                f"Invalid farm product IDs: {invalid_ids}"
            )
        return FarmProduct.objects.filter(id__in=existing_products)


class FarmExportSerializer(serializers.ModelSerializer):
    farm_type = serializers.SerializerMethodField()
    land_ownership = serializers.SerializerMethodField()
    size_metric = serializers.StringRelatedField()
    created_by = serializers.SerializerMethodField()
    farmer = serializers.SerializerMethodField()
    date_created = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True, allow_null=True)

    class Meta:
        model = Farm
        fields = (
            'farm_id', 'farm_type', 'type', 'name', 'location', 'district',
            'size', 'size_metric', 'livestock_kept', 'has_access_to_market',
            'irrigation', 'use_of_fertilizers', 'farming_methods',
            'provide_training', 'government_ngo_support', 'specify_support',
            'areas_of_assistance', 'land_ownership', 'other_specification',
            'farmer', 'created_by', 'date_created'
        )

    def get_farm_type(self, obj):
        return dict(Farm.FARM_TYPE_CHOICES).get(obj.farm_type, "")

    def get_land_ownership(self, obj):
        return dict(Farm.LAND_OWNERSHIP_CHOICES).get(obj.land_ownership, "")

    def get_created_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else ""

    def get_farmer(self, obj):
        if obj.farmer:
            return f"{obj.farmer.first_name} {obj.farmer.last_name}"
        return ""
