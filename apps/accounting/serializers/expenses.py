from rest_framework import serializers

from apps.accounting.models import Expense
from apps.inflow.serializers import ShortInflowOrderSerializer
from apps.outflow.serializers.outflow import ShortOutflowOrderSerializer


class ExpenseSerializer(serializers.ModelSerializer):
    order_detail = serializers.SerializerMethodField()

    class Meta:
        model = Expense
        fields = (
            'id', 'date_created', 'description',
            'amount', 'order_type', 'order_detail'
        )

    def get_order_detail(self, obj):
        if obj.order_type == 'inflow':
            return ShortInflowOrderSerializer(obj.order).data
        elif obj.order_type == 'outflow':
            return ShortOutflowOrderSerializer(obj.order).data
        return None
