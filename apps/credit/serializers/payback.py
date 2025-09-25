# serializers.py
from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.credit.models import Credit, CreditChangeLog, CreditPayback
from apps.credit.serializers.credits import ShortCreditSerializer
from apps.farm.models import Product
from apps.farm.serializers.products import ShortProductSerializer


class CreditPaybackSerializer(serializers.ModelSerializer):
    product = serializers.PrimaryKeyRelatedField(
        queryset=Product.objects.filter(is_active=True),
        required=False,
        allow_null=True
    )
    payment_status = serializers.ChoiceField(
        choices=[('full', 'Full Payment'), ('partial', 'Partial Payment')],
        write_only=True,
        required=True
    )

    class Meta:
        model = CreditPayback
        fields = [
            'id', 'credit', 'payback_method', 'amount',
            'product', 'quantity_bags', 'comments', 'date_paid', 'status',
            'payment_status'
        ]
        read_only_fields = ['id', 'outstanding', 'date_paid', 'status']

    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than zero.")

        return value

    def validate_credit(self, value):
        if self.initial_data['amount'] > value.outstanding_amount:
            raise serializers.ValidationError("Amount exceeds outstanding amount.")
        if value.payment_status == 'paid':
            raise serializers.ValidationError("This credit has already been fully paid.")
        if value.approval_status != 'approved':
            raise serializers.ValidationError("This credit has not been approved.")
        return value

    def create(self, validated_data):
        request = self.context['request']
        validated_data['created_by'] = request.user
        validated_data['organization'] = request.organization

        credit = validated_data['credit']
        amount = validated_data['amount']
        input_payment_status = validated_data.pop('payment_status')

        # Map input_payment_status to model's status field
        status = 'paid' if input_payment_status == 'full' else 'partial'

        old_status = credit.payment_status
        old_outstanding = credit.outstanding_amount

        with transaction.atomic():
            outstanding_before = credit.outstanding_amount
            new_outstanding = max(outstanding_before - amount, Decimal('0.00'))

            # Create payback with both values
            payback = CreditPayback.objects.create(
                **validated_data,
                outstanding_before=outstanding_before,
                outstanding_after=new_outstanding,
                status=status
            )

            # Update credit
            credit.outstanding_amount = new_outstanding
            credit.payment_status = status
            credit.save()

            # Log changes (optional but recommended)
            CreditChangeLog.objects.create(
                credit=credit,
                payback=payback,
                event='payment_created',
                field_name='outstanding_amount',
                old_value=str(old_outstanding),
                new_value=str(new_outstanding),
                notes=f"Payment of {amount} affected outstanding balance"
            )

            # Log changes (optional but recommended)
            CreditChangeLog.objects.create(
                credit=credit,
                payback=payback,
                event='payment_created',
                field_name='payment_status',
                old_value=old_status,
                new_value=status,
                notes=f"Payment of {amount} affected payment status"
            )

        return payback

    def update(self, instance, validated_data):
        credit = instance.credit
        old_amount = instance.amount
        new_amount = validated_data.get('amount', old_amount)
        old_outstanding = credit.outstanding_amount
        adjustment = old_amount - new_amount

        # Handle payment_status if provided in validated_data
        input_payment_status = validated_data.pop('payment_status', None)
        if input_payment_status:
            status = 'paid' if input_payment_status == 'full' else 'partial'
        else:
            status = instance.status # Keep existing status if not provided

        with transaction.atomic():
            # Lock related records
            credit = Credit.objects.select_for_update().get(pk=credit.id)
            payback = CreditPayback.objects.select_for_update().get(pk=instance.id)

            # Reverse old payment impact
            credit.outstanding_amount += old_amount

            # Apply new payment
            new_outstanding = max(credit.outstanding_amount - new_amount, Decimal('0.00'))

            # Update payback
            instance.amount = new_amount
            instance.outstanding_before = credit.outstanding_amount
            instance.outstanding_after = new_outstanding
            instance.status = status
            instance.save()

            # Update credit
            credit.outstanding_amount = new_outstanding
            credit.payment_status = status
            credit.save()

            # Log changes
            CreditChangeLog.objects.create(
                credit=credit,
                payback=instance,
                event='payment_updated',
                field_name='outstanding_amount',
                old_value=str(old_outstanding),
                new_value=str(new_outstanding),
                notes=f"Payment adjustment of {adjustment} affected outstanding balance"
            )

            return instance


class FullPaybackSerializer(serializers.ModelSerializer):
    credit = ShortCreditSerializer(read_only=True)
    product = ShortProductSerializer(read_only=True)
    payback_method = serializers.CharField(source='get_payback_method_display')
    status = serializers.CharField(source='get_status_display')
    outstanding_before = serializers.DecimalField(max_digits=10, decimal_places=2)
    outstanding_after = serializers.DecimalField(max_digits=10, decimal_places=2)
    created_by = ShortUserSerializer(read_only=True)

    class Meta:
        model = CreditPayback
        fields = [
            'id', 'credit', 'payback_method',
            'amount', 'outstanding_before', 'outstanding_after',
            'product', 'quantity_bags', 'comments', 'date_paid',
            'status', 'created_by', 'date_created'
        ]
        read_only_fields = fields


class PaybackExportSerializer(serializers.ModelSerializer):
    credit = serializers.SerializerMethodField()
    farmer = serializers.SerializerMethodField()
    payback_method = serializers.CharField(source='get_payback_method_display', read_only=True)
    product = serializers.SerializerMethodField()
    status = serializers.CharField(source='get_status_display', read_only=True)
    created_by = serializers.CharField(source='created_by.get_full_name', read_only=True)
    date_paid = serializers.DateField(format="%d-%m-%Y")
    date_created = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True, allow_null=True)

    class Meta:
        model = CreditPayback
        fields = (
            'credit', 'farmer', 'payback_method', 'amount', 'outstanding_before',
            'outstanding_after', 'product', 'quantity_bags', 'comments',
            'date_paid', 'status', 'created_by', 'date_created'
        )

    def get_credit(self, obj):
        return obj.credit.credit_id

    def get_farmer(self, obj):
        return f"{obj.credit.farmer.first_name} {obj.credit.farmer.last_name}"

    def get_product(self, obj):
        return obj.product.name if obj.product else ""