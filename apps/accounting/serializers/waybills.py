from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.customers.serializers import CustomerSerializer
from apps.inflow.models import InflowOrder
from apps.outflow.models import OutflowOrder
from apps.warehouse.serializers import ShortWarehouseSerializer


class InflowOrderListRetrieveSerializer(serializers.ModelSerializer):
    destination_warehouse = ShortWarehouseSerializer()
    aggregator = ShortUserSerializer()
    procurement_officer = ShortUserSerializer()

    class Meta:
        model = InflowOrder
        fields = (
            'id', 'order_id', 'waybill_id', 'status', 'date_created',
            'destination_warehouse', 'total_bags', 'order_total',
            'total_cost', 'date_created', 'aggregator', 'procurement_officer',
        )


class OutflowOrderListRetrieveSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer()
    procurement_officer = ShortUserSerializer()

    class Meta:
        model = OutflowOrder
        fields = (
            'id', 'order_id', 'waybill_id', 'customer', 'procurement_officer',
            'status', 'total_cost', 'expected_delivery_date', 'total_quantity',
            'destination', 'date_created',
        )
