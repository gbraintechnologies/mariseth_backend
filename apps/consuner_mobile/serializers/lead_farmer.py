from rest_framework import serializers

from apps.farm.models import Farm, Farmer


class SmallholderFarmerSerializer(serializers.ModelSerializer):
    farm_name = serializers.CharField(source='farm.name', read_only=True)
    farm_location = serializers.CharField(source='farm.location', read_only=True)
    phone_number = serializers.CharField(source='user.phone_number', read_only=True)

    class Meta:
        model = Farmer
        fields = [
            'id', 'farmer_id', 'first_name', 'last_name', 'phone_number',
            'gender', 'farm_name', 'farm_location', 'village', 'district'
        ]


class FarmSerializer(serializers.ModelSerializer):
    class Meta:
        model = Farm
        fields = (
            'id', 'farm_id', 'farm_type', 'type', 'name', 'location', 'region', 'district',
            'size', 'size_metric', 'livestock_kept', 'has_access_to_market',
            'irrigation', 'use_of_fertilizers', 'farming_methods', 'provide_training',
            'government_ngo_support', 'specify_support', 'areas_of_assistance',
            'land_ownership', 'other_specification', 'created_by', 'date_created',
        )
