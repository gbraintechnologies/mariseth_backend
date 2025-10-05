from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.customers.serializers import CustomerSerializer
from apps.inflow.models import InflowOrder
from apps.outflow.models import OutflowOrder, OutflowOrderWarehouseProduct
from apps.outflow.serializers.outflow import OutflowOrderDeliveryInfoResponseSerializer, OutflowOrderHistorySerializer, \
    OutflowOrderPaymentRequestSerializer, OutflowOrderWarehouseSerializer, OutflowWarehouseProductSerializer
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
            'total_cost', 'total_weight', 'date_created', 'aggregator', 'procurement_officer',
            'expected_amount', 'actual_amount'
        )


class OutflowOrderListRetrieveSerializer(serializers.ModelSerializer):
    customer = CustomerSerializer()
    procurement_officer = ShortUserSerializer()

    class Meta:
        model = OutflowOrder
        fields = (
            'id', 'order_id', 'waybill_id', 'customer', 'procurement_officer',
            'status', 'total_cost', 'expected_delivery_date', 'total_quantity',
            'total_weight', 'destination', 'date_created',
        )


class FullWaybillOutflowOrderSerializer(serializers.ModelSerializer):
    warehouses = OutflowOrderWarehouseSerializer(many=True,source='warehouses.all')
    customer = CustomerSerializer()
    procurement_officer = ShortUserSerializer()
    total_quantity = serializers.IntegerField()
    total_cost = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_weight = serializers.DecimalField(max_digits=12, decimal_places=2)
    delivery_information = OutflowOrderDeliveryInfoResponseSerializer(many=True)
    products = serializers.SerializerMethodField()
    payments = OutflowOrderPaymentRequestSerializer(many=True)
    logs = OutflowOrderHistorySerializer(source='history.all', many=True)

    class Meta:
        model = OutflowOrder
        fields = (
            'id', 'order_id', 'customer', 'procurement_officer',
            'destination', 'expected_delivery_date', 'status',
            'additional_costs', 'additional_cost_amount', 'total_quantity',
            'total_cost', 'total_weight', 'amount_paid', 'amount_due', 'products', 'warehouses',
            'delivery_information', 'payments', 'logs', 'waybill_id'
        )

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Sort warehouses by ID for consistent output
        representation['warehouses'] = sorted(
            representation['warehouses'],
            key=lambda x: x['id']
        )
        return representation

    def get_products(self, obj):
        all_products = OutflowOrderWarehouseProduct.objects.filter(
            outflow_order_warehouse__outflow_order=obj,
            is_active=True
        )
        return OutflowWarehouseProductSerializer(all_products, many=True).data