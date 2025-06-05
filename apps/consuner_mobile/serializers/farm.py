from rest_framework import serializers

from apps.farm.models import Farm, FarmProduct
from apps.farm.serializers.products import ShortProductSerializer


class FarmProductSerializer(serializers.ModelSerializer):
    product = ShortProductSerializer()

    class Meta:
        model = FarmProduct
        fields = ('id', 'product', 'is_main_product')
        read_only_fields = ('id',)


class FarmDetailSerializer(serializers.ModelSerializer):
    products = FarmProductSerializer(many=True, source='farmproduct_set')

    class Meta:
        model = Farm
        fields = (
            'id', 'farm_id', 'farm_type', 'type', 'name', 'location', 'region', 'district',
            'size', 'size_metric', 'livestock_kept', 'has_access_to_market',
            'irrigation', 'use_of_fertilizers', 'farming_methods', 'provide_training',
            'government_ngo_support', 'specify_support', 'areas_of_assistance',
            'land_ownership', 'other_specification', 'created_by', 'date_created',
            'products'
        )
        read_only_fields = ('id', 'created_by', 'updated_by', 'date_created')