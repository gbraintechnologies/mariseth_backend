from rest_framework import serializers
from apps.warehouse.models import Warehouse


class ShortWarehouseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Warehouse
        fields = ('id', 'warehouse_id', 'name')
