from rest_framework import serializers

from apps.ussd.models import UssdSession


class UssdRequestSerializer(serializers.Serializer):
    sessionID = serializers.CharField(max_length=100, source='session_id')
    userID = serializers.CharField(max_length=100, source='user_id', required=False, default='USSD_DOCUMENTATION')
    newSession = serializers.BooleanField(source='new_session', required=False, default=False)
    msisdn = serializers.CharField(max_length=20, source='phone_number')
    userData = serializers.CharField(source='user_data', required=False, allow_blank=True, default='')
    network = serializers.CharField(required=False, allow_blank=True, default='')


class UssdSessionSerializer(serializers.ModelSerializer):
    class Meta:
        model = UssdSession
        fields = (
            'id', 'session_id', 'phone_number', 'current_step', 'payload',
            'status', 'date_created', 'date_modified'
        )
        read_only_fields = ('id', 'date_created', 'date_modified')