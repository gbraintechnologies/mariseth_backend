from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.farm.models import FarmerRegistrationRequest
from apps.shared.serializers.regions import ShortRegionSerializer, DistrictSerializer


class FarmerRegistrationRequestResponseSerializer(serializers.ModelSerializer):
    district = DistrictSerializer()
    region = ShortRegionSerializer()
    reviewed_by = ShortUserSerializer()
    class Meta:
        model = FarmerRegistrationRequest
        fields = ('id', 'first_name'
                      , 'last_name'
                      , 'email'
                      , 'phone_number'
                      , 'district'
                      , 'region'
                      , 'id_type'
                      , 'id_number'
                      , 'date_of_birth'
                      , 'gender'
                      , 'reviewed_by'
                      , 'created_by'
                      , 'status'
                      , 'request_channel'
                      , 'reviewed_at'
                      , 'comments'
                      , 'country'
                      ,)
        read_only_fields = ('id',)

class FarmerRegistrationRequestSerializer(serializers.Serializer):
    comments = serializers.CharField(max_length=100,required=True, allow_blank=False)

