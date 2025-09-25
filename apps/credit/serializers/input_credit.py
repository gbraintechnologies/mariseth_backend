from django.db import transaction
from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.credit.models import InputCredit, InputCreditPurchase
from apps.shared.models import CustomType
from apps.shared.serializers.custom_types import CustomTypeSerializer
from apps.warehouse.models import Warehouse


class FullInputCreditSerializer(serializers.ModelSerializer):
    category = CustomTypeSerializer()
    created_by = ShortUserSerializer()

    class Meta:
        model = InputCredit
        fields = (
            'id', 'input_credit_id', 'category', 'name', 'price',
            'weight', 'quantity', 'date_created', 'created_by'
        )


class InputCreditPurchaseSerializer(serializers.ModelSerializer):
    input_credit = serializers.PrimaryKeyRelatedField(
        queryset=InputCredit.objects.filter(is_active=True), required=True
    )
    quantity = serializers.IntegerField(required=True)
    notes = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    purchase_date = serializers.DateField(required=True)
    warehouse = serializers.PrimaryKeyRelatedField(
        queryset=Warehouse.objects.filter(is_active=True), required=True
    )

    class Meta:
        model = InputCreditPurchase
        fields = (
            'id', 'input_credit', 'purchase_date',
            'source', 'warehouse', 'quantity', 'notes',
        )

        read_only_fields = ('id', 'date_created', 'date_modified', 'created_by', 'is_active')

    def create(self, validated_data):
        request = self.context.get('request')
        input_credit = validated_data['input_credit']
        
        with transaction.atomic():
            validated_data['total_price'] = input_credit.price * validated_data['quantity']
            validated_data['total_weight'] = input_credit.weight * validated_data['quantity']
            validated_data['created_by'] = request.user
            validated_data['organization'] = request.organization
            input_credit_purchase = InputCreditPurchase.objects.create(**validated_data)
            input_credit_purchase.add_input_credits(price=input_credit.price, weight=input_credit.weight)
            input_credit_purchase.input_credit_purchase_id = f'ICP-{input_credit_purchase.id:02d}'
            input_credit_purchase.save(update_fields=['input_credit_purchase_id'])

        return input_credit_purchase


class InputCreditPurchaseListSerializer(serializers.ModelSerializer):
    input_credit = FullInputCreditSerializer()
    created_by = ShortUserSerializer()

    class Meta:
        model = InputCreditPurchase
        fields = (
            'id', 'input_credit_purchase_id', 'input_credit',
            'purchase_date', 'source', 'warehouse', 'quantity',
            'total_price', 'notes', 'total_weight', 'date_created',
            'created_by'
        )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from apps.warehouse.serializers import ShortWarehouseSerializer
        self.fields['warehouse'] = ShortWarehouseSerializer()


class CreateInputCreditSerializer(serializers.ModelSerializer):
    class Meta:
        model = InputCredit
        fields = ('category', 'name', 'price', 'weight')
