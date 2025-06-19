from django.utils import timezone
from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.credit.models import Credit, CreditChangeLog, CreditPayback
from apps.credit.utils import generate_credit_id
from apps.farm.serializers.farmer import ShortFarmerSerializer
from apps.shared.serializers.custom_types import CustomTypeSerializer


class ShortCreditSerializer(serializers.ModelSerializer):
    farmer = ShortFarmerSerializer()
    payment_status = serializers.CharField(source='get_payment_status_display')
    quantity_metric = CustomTypeSerializer()

    class Meta:
        model = Credit
        fields = (
            'id', 'farmer', 'input_credits', 'type', 'quantity',
            'quantity_metric', 'credit_amount', 'issue_date', 'due_date',
            'interest_rate', 'payment_status', 'approval_status', 'notes'
        )
        read_only_fields = fields


class CreditSerializer(serializers.ModelSerializer):
    class Meta:
        model = Credit
        fields = (
            'id', 'farmer', 'input_credits', 'type', 'quantity',
            'quantity_metric', 'credit_amount', 'issue_date', 'due_date',
            'interest_rate', 'payment_status', 'approval_status', 'notes'
        )
        read_only_fields = ('id', 'approval_status')

    def validate(self, data):
        if data.get('due_date') and data.get('issue_date'):
            if data['due_date'] <= data['issue_date']:
                raise serializers.ValidationError("Due date must be after issue date")
        return data

    def create(self, validated_data):
        request = self.context['request']
        validated_data['created_by'] = request.user
        validated_data['organization'] = request.organization
        validated_data['credit_id'] = generate_credit_id(request.organization.id)
        interest_amount = validated_data['credit_amount'] * (validated_data['interest_rate'] / 100)
        validated_data['outstanding_amount'] = validated_data['credit_amount'] + interest_amount

        return super().create(validated_data)

    def update(self, instance, validated_data):
        changes = []
        if 'credit_amount' in validated_data:
            old_amount = instance.credit_amount
            new_amount = validated_data['credit_amount']
            if old_amount != new_amount:
                changes.append(('credit_amount', old_amount, new_amount))
                # Recalculate outstanding
                validated_data['outstanding_amount'] = new_amount * instance.interest_rate

        # Track interest rate changes
        if 'interest_rate' in validated_data:
            old_interest = instance.interest_rate
            new_interest = validated_data['interest_rate']
            if old_interest != new_interest:
                changes.append(('interest_rate', old_interest, new_interest))
                # Recalculate outstanding
                validated_data['outstanding_amount'] = instance.credit_amount * new_interest

        # Track outstanding changes
        if 'outstanding_amount' in validated_data:
            old_outstanding = instance.outstanding_amount
            new_outstanding = validated_data['outstanding_amount']
            if old_outstanding != new_outstanding:
                changes.append(('outstanding_amount', old_outstanding, new_outstanding))

        # Apply updates
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        # Log changes
        for field, old, new in changes:
            CreditChangeLog.objects.create(
                credit=instance,
                event='field_updated',
                field_name=field,
                old_value=str(old),
                new_value=str(new),
                notes=f"{field} changed from {old} to {new}"
            )

        return instance


class CreditChangeLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = CreditChangeLog
        fields = (
            'id', 'event', 'field_name', 'old_value', 'new_value', 'created_by', 'date_created'
        )


class FullCreditSerializer(serializers.ModelSerializer):
    created_by = ShortUserSerializer()
    farmer = ShortFarmerSerializer()
    payment_status = serializers.CharField(source='get_payment_status_display')
    quantity_metric = CustomTypeSerializer()
    logs = serializers.SerializerMethodField()

    class Meta:
        model = Credit
        fields = (
            'id', 'farmer', 'input_credits', 'type', 'quantity',
            'quantity_metric', 'credit_amount', 'issue_date', 'due_date',
            'interest_rate', 'payment_status', 'approval_status', 'notes',
            'created_by', 'outstanding_amount', 'denial_notes',
            'self_application', 'logs'
        )
        read_only_fields = fields

    def get_logs(self, obj):
        return CreditChangeLogSerializer(obj.history.filter(is_active=True), many=True).data


class CreditDeleteSerializer(serializers.Serializer):

    def validate(self, attrs):
        credit = self.instance
        if credit.approval_status != 'inactive':
            raise serializers.ValidationError(
                "Cannot delete active credit."
            )
        if CreditPayback.objects.filter(credit=credit, is_active=True).exists():
            raise serializers.ValidationError(
                "Cannot delete credit with active paybacks."
            )
        return attrs


class CreditApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'deny'], required=True,
                                     help_text="Approval action to perform")
    denial_notes = serializers.CharField(required=False, allow_blank=True,
                                         help_text="Required when rejecting a credit application")

    def validate(self, attrs):
        credit = self.context['credit']
        action = attrs['action']

        if action == 'approve' and credit.approval_status == 'approved':
            raise serializers.ValidationError({'action': 'Credit already approved'})
        if action == 'deny':
            if credit.approval_status == 'denied':
                raise serializers.ValidationError({'action': 'Credit already Denied'})
        return attrs

    def save(self):
        credit = self.context['credit']
        request = self.context['request']
        action = self.validated_data['action']
        old_status = credit.approval_status

        credit.approval_status = 'approved' if action == 'approve' else 'denied'
        credit.issued_date = timezone.now() if action == 'approve' else None
        credit.denial_notes = self.validated_data.get('denial_notes', '')
        credit.payment_status = 'active' if action == 'approve' else 'inactive'
        credit.save()

        CreditChangeLog.objects.create(
            credit=credit,
            event='approved' if action == 'approve' else 'denied',
            field_name='approval_status',
            old_value=old_status,
            new_value=credit.approval_status,
            created_by=request.user
        )
        return credit


class CreditExportSerializer(serializers.ModelSerializer):
    farmer = serializers.SerializerMethodField()
    payment_status = serializers.SerializerMethodField()
    approval_status = serializers.SerializerMethodField()
    created_by = serializers.SerializerMethodField()
    issue_date = serializers.DateField(format="%d-%m-%Y")
    due_date = serializers.DateField(format="%d-%m-%Y")
    date_created = serializers.DateTimeField(format="%d-%m-%Y %H:%M:%S", read_only=True, allow_null=True)
    quantity = serializers.SerializerMethodField()

    class Meta:
        model = Credit
        fields = (
            'id', 'farmer', 'type', 'quantity',
            'credit_amount', 'issue_date', 'due_date', 'interest_rate',
            'outstanding_amount', 'payment_status', 'approval_status',
            'main_crops', 'created_by', 'date_created'
        )

    def get_farmer(self, obj):
        return f"{obj.farmer.first_name} {obj.farmer.last_name}" if obj.farmer else ""

    def get_payment_status(self, obj):
        return dict(Credit.PAYMENT_STATUS_CHOICES).get(obj.payment_status, "")

    def get_approval_status(self, obj):
        return dict(Credit.APPROVAL_STATUS_CHOICES).get(obj.approval_status, "")

    def get_created_by(self, obj):
        return f"{obj.created_by.first_name} {obj.created_by.last_name}" if obj.created_by else ""

    def get_quantity(self, obj):
        return f"{obj.quantity} {obj.quantity_metric.name}"
