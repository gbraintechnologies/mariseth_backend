from rest_framework import serializers

from apps.farm.models import Farm, Farmer
from apps.farm.utils import generate_farmer_id
from apps.shared.models import District, Region


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


class MobileAddSmallholderFarmerSerializer(serializers.ModelSerializer):
    farm = serializers.PrimaryKeyRelatedField(
        queryset=Farm.objects.filter(is_active=True),
        required=False,
        allow_null=True,
    )
    district = serializers.PrimaryKeyRelatedField(
        queryset=District.objects.all(),
        required=False,
        allow_null=True,
    )
    region = serializers.PrimaryKeyRelatedField(
        queryset=Region.objects.all(),
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Farmer
        fields = (
            'id', 'first_name', 'last_name', 'other_names', 'gender',
            'date_of_birth', 'id_number', 'phone_number', 'email', 'address',
            'village', 'region', 'district', 'country', 'farm', 'id_type',
        )
        read_only_fields = ('id',)

    def validate(self, data):
        if data.get('district') and not data.get('region'):
            raise serializers.ValidationError(
                {'region': 'Region must be provided when district is specified.'}
            )
        return data

    def create(self, validated_data):
        request = self.context['request']
        validated_data['type'] = 'smallholder'
        validated_data['created_by'] = request.user
        validated_data['organization'] = request.organization
        validated_data['farmer_id'] = generate_farmer_id(request.organization.id)
        validated_data['lead_farmer'] = request.user.farmer
        return super().create(validated_data)
