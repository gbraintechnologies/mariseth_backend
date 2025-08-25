from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.inflow.models import InflowOrderHistory
from apps.inflow.serializers import ShortInflowOrderSerializer
from apps.outflow.models import OutflowOrderHistory
from apps.outflow.serializers.outflow import ShortOutflowOrderSerializer


class OutflowOrderHistorySerializer(serializers.ModelSerializer):
    order = ShortOutflowOrderSerializer(source='outflow_order')
    created_by = ShortUserSerializer()

    class Meta:
        model = OutflowOrderHistory
        fields = [
            'id', 'order',  'field_name', 'old_value', 'new_value',
            'is_active', 'created_by', 'date_created',
        ]


class InflowOrderHistorySerializer(serializers.ModelSerializer):
    order = ShortInflowOrderSerializer()
    created_by = ShortUserSerializer()

    class Meta:
        model = InflowOrderHistory
        fields = [
            'id', 'order',  'notes', 'old_value', 'new_value', 'field_name',
            'is_active', 'created_by', 'date_created'
        ]
