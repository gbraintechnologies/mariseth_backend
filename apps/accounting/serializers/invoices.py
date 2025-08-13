from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.customers.serializers import ShortCustomerSerializer
from apps.outflow.models import OutflowOrderPayments
from apps.outflow.serializers.outflow import ShortOutflowOrderSerializer


class InvoiceSerializer(serializers.ModelSerializer):
    outflow_order = ShortOutflowOrderSerializer(read_only=True)
    customer = ShortCustomerSerializer(source='outflow_order.customer', read_only=True)
    created_by = ShortUserSerializer(read_only=True)
    quantity = serializers.CharField(source='outflow_order.total_quantity', read_only=True)
    total_cost = serializers.CharField(source='outflow_order.total_cost', read_only=True)
    total_weight = serializers.CharField(source='outflow_order.total_weight', read_only=True)

    class Meta:
        model = OutflowOrderPayments
        fields = (
            'id', 'invoice_id', 'outflow_order', 'amount_paid',
            'payment_type', 'payment_method', 'paid_to', 'customer',
            'date_created', 'created_by', 'amount_due', 'quantity',
            'total_cost', 'total_weight'
        )
        read_only_fields = fields
