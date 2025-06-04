from rest_framework import serializers

from apps.credit.models import Credit, CreditPayback


class MobileCreditSerializer(serializers.ModelSerializer):
    quantity_metric_name = serializers.CharField(source='quantity_metric.name', read_only=True)
    days_overdue = serializers.SerializerMethodField()

    class Meta:
        model = Credit
        fields = [
            'id', 'credit_id',
            'input_credits', 'type', 'quantity', 'quantity_metric_name', 'notes',
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

    class Meta:
        model = Credit
        fields = [
            'id', 'credit_id', 'input_credits', 'type', 'quantity',
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
