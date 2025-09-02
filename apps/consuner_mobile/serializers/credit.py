from decimal import Decimal
from rest_framework import serializers

from apps.credit.models import Credit, CreditPayback, InputCredit
from apps.credit.utils import generate_credit_id
from apps.shared.models import CustomType


class MobileCreditSerializer(serializers.ModelSerializer):
    quantity_metric_name = serializers.CharField(source='quantity_metric.name', read_only=True)
    days_overdue = serializers.SerializerMethodField()
    input_credit_category = serializers.CharField(source='input_credit_category.name', read_only=True)
    input_credit = serializers.CharField(source='input_credit.name', read_only=True)

    class Meta:
        model = Credit
        fields = [
            'id', 'credit_id',
            'input_credit_category', 'input_credit', 'quantity', 'quantity_metric_name', 'notes',
            'credit_amount', 'issue_date', 'due_date', 'interest_rate',
            'outstanding_amount', 'payment_status', 'approval_status',
            'days_overdue', 'date_created'
        ]

    def get_days_overdue(self, obj):
        if obj.due_date and obj.payment_status != 'paid':
            from datetime import date
            today = date.today()
            if today > obj.due_date:
                return (today - obj.due_date).days
        return 0


class MobileCreditPaybackSerializer(serializers.ModelSerializer):
    credit_id = serializers.CharField(source='credit.credit_id', read_only=True)
    credit_type = serializers.CharField(source='credit.type', read_only=True)
    credit_amount = serializers.DecimalField(source='credit.credit_amount', max_digits=10, decimal_places=2,
                                             read_only=True)
    product_name = serializers.CharField(source='product.name', read_only=True)

    class Meta:
        model = CreditPayback
        fields = [
            'id', 'credit_id', 'credit_type', 'credit_amount', 'payback_method',
            'amount', 'outstanding_before', 'outstanding_after', 'product_name',
            'quantity_bags', 'comments', 'date_paid', 'status', 'date_created'
        ]


class MobileActiveCreditSerializer(serializers.ModelSerializer):
    quantity_metric_name = serializers.CharField(source='quantity_metric.name', read_only=True)
    days_overdue = serializers.SerializerMethodField()
    total_paid = serializers.SerializerMethodField()
    recent_paybacks = MobileCreditPaybackSerializer(source='paybacks', many=True, read_only=True)
    input_credit_category = serializers.CharField(source='input_credit_category.name', read_only=True)
    input_credit = serializers.CharField(source='input_credit.name', read_only=True)

    class Meta:
        model = Credit
        fields = [
            'id', 'credit_id', 'input_credit_category', 'input_credit', 'quantity',
            'quantity_metric_name', 'notes',
            'credit_amount', 'issue_date', 'due_date', 'interest_rate',
            'outstanding_amount', 'payment_status', 'approval_status',
            'days_overdue', 'total_paid', 'recent_paybacks', 'date_created'
        ]

    def get_days_overdue(self, obj):
        if obj.due_date and obj.payment_status != 'paid':
            from datetime import date
            today = date.today()
            if today > obj.due_date:
                return (today - obj.due_date).days
        return 0

    def get_total_paid(self, obj):
        return obj.credit_amount - obj.outstanding_amount


class MobileCreditApplicationSerializer(serializers.ModelSerializer):
    input_credit_category = serializers.PrimaryKeyRelatedField(queryset=CustomType.objects.filter(is_active=True))
    input_credit = serializers.PrimaryKeyRelatedField(queryset=InputCredit.objects.filter(is_active=True).all())

    class Meta:
        model = Credit
        fields = (
            'input_credit_category', 'input_credit', 'quantity',
            'quantity_metric', 'notes', 'self_application',
        )

    def validate(self, data):
        if data.get('due_date') and data.get('issue_date'):
            if data['due_date'] <= data['issue_date']:
                raise serializers.ValidationError("Due date must be after issue date")
        return data

    def create(self, validated_data):
        request = self.context['request']
        validated_data['farmer'] = request.user.farmer
        validated_data['created_by'] = request.user
        validated_data['organization'] = request.organization
        validated_data['credit_id'] = generate_credit_id(request.organization.id)
        validated_data['self_application'] = True

        # Get input_credit and quantity
        input_credit = validated_data.get('input_credit')
        quantity = validated_data.get('quantity')

        # Calculate credit_amount based on input_credit price and quantity
        if input_credit and quantity is not None:
            # Ensure input_credit.price is Decimal for calculation
            input_credit_price = Decimal(str(input_credit.price))
            calculated_credit_amount = input_credit_price * Decimal(str(quantity))
            validated_data['credit_amount'] = calculated_credit_amount
        else:
            # If input_credit or quantity is missing, use 0 or raise error if credit_amount is required
            validated_data['credit_amount'] = Decimal('0.00') # Or handle as an error if credit_amount is mandatory

        # Calculate outstanding_amount
        credit_amount = validated_data.get('credit_amount', Decimal('0.00'))
        interest_rate = validated_data.get('interest_rate', Decimal('0.00'))

        interest_amount = credit_amount * (interest_rate / Decimal('100.00'))
        validated_data['outstanding_amount'] = credit_amount + interest_amount

        return super().create(validated_data)
