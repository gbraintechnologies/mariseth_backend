from decimal import Decimal
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.credit.models import Credit, CreditChangeLog, CreditPayback, InputCredit, CreditWarehouse
from apps.credit.serializers.input_credit import FullInputCreditSerializer
from apps.credit.utils import generate_credit_id
from apps.farm.models import Farmer
from apps.farm.serializers.farmer import ShortFarmerSerializer
from apps.shared.models import CustomType
from apps.shared.serializers.custom_types import CustomTypeSerializer
from apps.warehouse.models import Warehouse, InputCreditWarehouse
from apps.warehouse.serializers import ShortWarehouseSerializer


class ShortCreditSerializer(serializers.ModelSerializer):
    farmer = ShortFarmerSerializer()
    payment_status = serializers.CharField(source='get_payment_status_display')
    quantity_metric = CustomTypeSerializer()
    input_credit = FullInputCreditSerializer()

    class Meta:
        model = Credit
        fields = (
            'id', 'credit_id', 'farmer', 'input_credit', 'quantity',
            'quantity_metric', 'credit_amount', 'issue_date', 'due_date',
            'interest_rate', 'payment_status', 'approval_status', 'notes'
        )
        read_only_fields = fields


class CreditSerializer(serializers.ModelSerializer):
    farmer = serializers.PrimaryKeyRelatedField(queryset=Farmer.objects.all())
    input_credit_category = serializers.PrimaryKeyRelatedField(queryset=CustomType.objects.filter(is_active=True))
    input_credit = serializers.PrimaryKeyRelatedField(queryset=InputCredit.objects.filter(is_active=True).all())
    quantity_metric = serializers.PrimaryKeyRelatedField(
        queryset=CustomType.objects.filter(category_name='quantity_metric'))

    class Meta:
        model = Credit
        fields = (
            'id', 'farmer', 'input_credit_category', 'input_credit', 'quantity',
            'quantity_metric', 'notes', 'self_application',
        )
        read_only_fields = ('id', 'payment_status', 'approval_status', 'outstanding_amount')


    def create(self, validated_data):
        request = self.context['request']
        validated_data['created_by'] = request.user
        validated_data['organization'] = request.organization
        validated_data['credit_id'] = generate_credit_id(request.organization.id)

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
            validated_data['credit_amount'] = Decimal('0.00')  # Or handle as an error if credit_amount is mandatory

        # Calculate outstanding_amount
        credit_amount = validated_data.get('credit_amount', Decimal('0.00'))
        interest_rate = validated_data.get('interest_rate', Decimal('0.00'))

        interest_amount = credit_amount * (interest_rate / Decimal('100.00'))
        validated_data['outstanding_amount'] = credit_amount + interest_amount

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
                notes=f"{field} changed from {old} to {new}",
                created_by=self.context['request'].user
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
    input_credit = FullInputCreditSerializer()

    class Meta:
        model = Credit
        fields = (
            'id', 'credit_id', 'farmer', 'input_credit', 'quantity',
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


class CreditWarehouseAllocationSerializer(serializers.Serializer):
    warehouse = serializers.PrimaryKeyRelatedField(queryset=Warehouse.objects.all())
    quantity = serializers.IntegerField()


class CreditApprovalSerializer(serializers.Serializer):
    action = serializers.ChoiceField(choices=['approve', 'deny'], required=True,
                                     help_text="Approval action to perform")
    denial_notes = serializers.CharField(required=False, allow_blank=True,
                                         help_text="Required when rejecting a credit application")
    credit_amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=False, allow_null=True)
    interest_rate = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)
    issue_date = serializers.DateField(required=False, allow_null=True)
    due_date = serializers.DateField(required=False, allow_null=True)
    notes = serializers.CharField(required=False, allow_blank=True)
    warehouses = CreditWarehouseAllocationSerializer(many=True, required=False)

    def validate(self, attrs):
        credit = self.context['credit']
        action = attrs['action']

        if action == 'approve':
            if credit.approval_status == 'approved':
                raise serializers.ValidationError({'action': 'Credit already approved'})
            # If approving, warehouses list is required
            if not attrs.get('warehouses'):
                raise serializers.ValidationError({'warehouses': 'Warehouse allocations are required for approval'})
            if not isinstance(attrs['warehouses'], list) or not all(
                    isinstance(item, dict) for item in attrs['warehouses']):
                raise serializers.ValidationError({'warehouses': 'Warehouses must be a list of objects.'})

            total_allocated_quantity = 0
            for allocation in attrs['warehouses']:
                if 'warehouse' not in allocation or 'quantity' not in allocation:
                    raise serializers.ValidationError(
                        {'warehouses': 'Each warehouse allocation must contain a warehouse ID and quantity.'})

                # Validate stock in warehouse
                warehouse_instance = allocation['warehouse']
                requested_quantity = allocation['quantity']

                try:
                    # Import InputCreditWarehouse here to avoid circular dependency at top level
                    from apps.warehouse.models import InputCreditWarehouse
                    input_credit_warehouse = InputCreditWarehouse.objects.get(
                        input_credit=credit.input_credit,
                        warehouse=warehouse_instance
                    )
                    if input_credit_warehouse.quantity < requested_quantity:
                        raise serializers.ValidationError(
                            {
                                'warehouses': f'Insufficient stock for input credit {credit.input_credit.name} in warehouse {input_credit_warehouse.warehouse.name}. Available: {input_credit_warehouse.quantity}, Requested: {requested_quantity}'}
                        )
                    total_allocated_quantity += requested_quantity
                except InputCreditWarehouse.DoesNotExist:
                    raise serializers.ValidationError(
                        {
                            'warehouses': f'Input credit {credit.input_credit.name} not found in warehouse {warehouse_instance.name}.'}
                    )

            if total_allocated_quantity != credit.quantity:
                raise serializers.ValidationError(
                    {
                        'warehouses': f'Total allocated quantity ({total_allocated_quantity}) must match credit quantity ({credit.quantity}).'}
                )

        elif action == 'deny':
            if credit.approval_status == 'denied':
                raise serializers.ValidationError({'action': 'Credit already Denied'})
            # If denying, warehouse and quantity should not be provided
            if attrs.get('warehouses'):
                raise serializers.ValidationError('Warehouse allocations should not be provided when denying a credit.')
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
        credit.notes = self.validated_data.get('notes', credit.notes)  # Update notes

        if action == 'approve':
            # Update credit fields from validated data
            credit.credit_amount = self.validated_data.get('credit_amount', credit.credit_amount)
            credit.interest_rate = self.validated_data.get('interest_rate', credit.interest_rate)
            credit.issue_date = self.validated_data.get('issue_date', credit.issue_date)
            credit.due_date = self.validated_data.get('due_date', credit.due_date)

            # Calculate outstanding_amount
            credit_amount = credit.credit_amount
            interest_rate = credit.interest_rate

            interest_amount = credit_amount * (interest_rate / Decimal('100.00'))
            credit.outstanding_amount = credit_amount + interest_amount

            # Create CreditWarehouse entries for each allocation
            for allocation_data in self.validated_data['warehouses']:
                warehouse_instance = allocation_data['warehouse']
                CreditWarehouse.objects.create(
                    credit=credit,
                    input_credit=credit.input_credit,
                    warehouse=warehouse_instance,
                    quantity=allocation_data['quantity'],
                )
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


class CreditWarehouseSerializer(serializers.ModelSerializer):
    warehouse = ShortWarehouseSerializer()
    warehouse_input_credit_quantity = serializers.SerializerMethodField()
    credit = serializers.SerializerMethodField()  # This now contains full credit details

    class Meta:
        model = CreditWarehouse
        fields = (
            'id', 'credit', 'warehouse', 'quantity', 'is_fulfilled',
            'warehouse_input_credit_quantity'
        )
        read_only_fields = fields

    def get_warehouse_input_credit_quantity(self, obj):
        try:
            input_credit_warehouse = InputCreditWarehouse.objects.get(
                warehouse=obj.warehouse,
                input_credit=obj.input_credit
            )
            return input_credit_warehouse.quantity
        except InputCreditWarehouse.DoesNotExist:
            return 0

    def get_credit(self, obj):
        # Include more credit details as needed
        return ShortCreditSerializer(obj.credit).data


class WarehouseManagerFulfillCreditSerializer(serializers.Serializer):
    def validate(self, attrs):
        credit = self.context['credit']
        warehouse = self.context['warehouse']
        user = self.context['request'].user

        # Permission check
        if not user.is_superuser and user not in warehouse.managers.all():
            raise serializers.ValidationError("You are not a manager of this warehouse.")

        # Credit status check
        if credit.approval_status not in ['approved']:  # Only approved credits can be fulfilled
            raise serializers.ValidationError("Credit must be approved before fulfillment.")

        # Check if already fulfilled for this warehouse
        if credit.creditwarehouse_set.filter(warehouse=warehouse, is_fulfilled=True).exists():
            raise serializers.ValidationError("This credit has already been fulfilled for this warehouse.")

        return attrs

    def save(self):
        credit = self.context['credit']
        warehouse = self.context['warehouse']
        user = self.context['request'].user

        # Fulfill the warehouse allocation
        credit.decrease_input_credit_for_warehouse(warehouse)

        # Check if all allocations are now fulfilled
        if not credit.creditwarehouse_set.filter(is_fulfilled=False).exists():
            old_status = credit.approval_status
            credit.approval_status = 'fulfilled'  # Changed from payment_status to approval_status
            credit.save()

            # Log the status change
            CreditChangeLog.objects.create(
                credit=credit,
                event='status_change',
                field_name='approval_status',  # Changed from payment_status
                old_value=old_status,
                new_value='fulfilled',
                created_by=None,
                notes='Credit automatically marked as fulfilled after all warehouse allocations were completed.'
            )

        return credit