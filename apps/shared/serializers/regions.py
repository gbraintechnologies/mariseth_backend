from rest_framework import serializers

from apps.shared.models import District, Region


class DistrictSerializer(serializers.ModelSerializer):
    class Meta:
        model = District
        fields = ['id','name']


class RegionSerializer(serializers.ModelSerializer):
    districts = DistrictSerializer(many=True, read_only=True)

    class Meta:
        model = Region
        fields = ['id', 'name', 'code', 'districts']


class ShortRegionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Region
        fields = ['id', 'name', 'code']
