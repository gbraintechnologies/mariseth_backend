from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.farm.models import Farm, FarmProduct, Product
from apps.farm.serializers.products import ShortProductSerializer
from apps.farm.utils import generate_farm_id
from apps.shared.models import District, Region
from apps.shared.serializers.custom_types import CustomTypeSerializer
from apps.shared.serializers.regions import DistrictSerializer, ShortRegionSerializer


class ShortFarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = ('id', 'name', 'farm_id', 'land_ownership')


class FarmProductSerializer(serializers.ModelSerializer):
    product = ShortProductSerializer()

    class Meta:
        model = FarmProduct
        fields = ('id', 'product', 'is_main_product')
        read_only_fields = ('id',)


class FarmSerializer(serializers.ModelSerializer):
    region = serializers.PrimaryKeyRelatedField(queryset=Region.objects.all(), required=False)
    district = serializers.PrimaryKeyRelatedField(queryset=District.objects.all(), required=False)
    livestock = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True), required=False
                                                 ), required=False, allow_null=True)
    crops = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(queryset=Product.objects.filter(is_active=True), required=False
                                                 ), required=False, allow_null=True)
    land_ownership = serializers.CharField(required=False, allow_null=True)

    class Meta:
        model = Farm
        fields = (
            'id', 'farm_type', 'type', 'name', 'location', 'region', 'district',
            'size', 'size_metric', 'livestock_kept', 'has_access_to_market',
            'irrigation', 'use_of_fertilizers', 'farming_methods', 'provide_training',
            'government_ngo_support', 'specify_support', 'areas_of_assistance',
            'land_ownership', 'other_specification', 'livestock', 'crops', 'farmer'
        )
        read_only_fields = ('id',)

    def validate(self, data):
        if data.get('district') and not data.get('region'):
            raise serializers.ValidationError(
                {'region': 'Region must be provided when district is specified.'}
            )
        for field in data.keys():
            if field not in self.Meta.fields:
                raise serializers.ValidationError({field: "Invalid field."})
        return data

    def create(self, validated_data):
        request = self.context['request']
        validated_data['created_by'] = request.user
        validated_data['organization'] = request.organization
        validated_data['farm_id'] = generate_farm_id(validated_data['name'])
        livestock = validated_data.pop('livestock', [])
        crops = validated_data.pop('crops', [])
        farm = Farm.objects.create(**validated_data)
        if livestock:
            for livestock_data in livestock:
                FarmProduct.objects.create(farm=farm, product=livestock_data, is_main_product=True)
        if crops:
            for crop_data in crops:
                FarmProduct.objects.create(farm=farm, product=crop_data, is_main_product=True)
        return farm

    def update(self, instance, validated_data):
        # TODO: ADD SIGNALS TO LOG CHANGES
        incoming_crop_products = validated_data.pop('crops', [])
        incoming_livestock_products = validated_data.pop('livestock', [])
        desired_products_for_farm = set(incoming_crop_products + incoming_livestock_products)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        current_farm_product_relations = instance.farmproduct_set.all()
        for existing_relation in current_farm_product_relations:
            if existing_relation.product not in desired_products_for_farm and existing_relation.is_active:
                existing_relation.is_active = False
                existing_relation.save()
        for product_to_be_linked in desired_products_for_farm:
            relation, created = instance.farmproduct_set.get_or_create(
                product=product_to_be_linked,
                defaults={'is_main_product': False, 'is_active': True}
            )
            if not created and not relation.is_active:
                relation.is_active = True
                relation.save()
        return instance


class FullFarmSerializer(serializers.ModelSerializer):
    created_by = ShortUserSerializer()
    crops = serializers.SerializerMethodField()
    livestock = serializers.SerializerMethodField()
    region = ShortRegionSerializer()
    district = DistrictSerializer()
    size_metric = CustomTypeSerializer()
    farmer = serializers.SerializerMethodField()

    class Meta:
        model = Farm
        fields = (
            'id', 'farm_id', 'farm_type', 'type', 'name', 'location', 'region', 'district',
            'size', 'size_metric', 'livestock_kept', 'has_access_to_market',
            'irrigation', 'use_of_fertilizers', 'farming_methods', 'provide_training',
            'government_ngo_support', 'specify_support', 'areas_of_assistance',
            'land_ownership', 'other_specification', 'created_by', 'date_created',
            'crops', 'livestock', 'farmer'
        )
        read_only_fields = ('id', 'created_by', 'updated_by', 'date_created')

    def get_crops(self, obj):
        crop_products = obj.farmproduct_set.filter(
            is_active=True,
            product__type='crop'
        )
        return FarmProductSerializer(crop_products, many=True).data

    def get_livestock(self, obj):
        livestock_products = obj.farmproduct_set.filter(
            is_active=True,
            product__type='livestock'
        )
        return FarmProductSerializer(livestock_products, many=True).data

    def get_farmer(self, obj):
        if obj.farmer is not None:
            return {
                'id': obj.farmer.id,
                'first_name': obj.farmer.first_name,
                'last_name': obj.farmer.last_name,
                'type': obj.farmer.type,
                'phone_number': obj.farmer.phone_number
            }
        return None


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
    region = serializers.StringRelatedField(source='region.name')
    district = serializers.StringRelatedField(source='district.name')

    class Meta:
        model = Farm
        fields = (
            'farm_id', 'farm_type', 'type', 'name', 'location', 'region', 'district',
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
