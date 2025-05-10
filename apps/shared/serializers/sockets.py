from rest_framework import serializers


class SocketDataSerializer(serializers.Serializer):
    message_type = serializers.CharField(required=True)
    payload = serializers.JSONField(required=True)