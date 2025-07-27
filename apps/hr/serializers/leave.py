from django.db import transaction
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.hr.models import LeaveRequest, LeaveType
from apps.hr.serializers.employee import ShortEmployeeSerializer
from apps.hr.utils import generate_leave_id


class LeaveTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LeaveType
        fields = (
            'id', 'name', 'description', 'max_days',
            'deducts_from_allowance', 'deduct_from'
        )

    def create(self, validated_data):
        request = self.context['request']
        validated_data['organization'] = request.organization
        validated_data['created_by'] = request.user
        leave_type = LeaveType.objects.create(**validated_data)
        return leave_type

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = self.context['request'].user
        instance.updated_at = timezone.now()
        instance.save()
        return instance


class LeaveRequestSerializer(serializers.ModelSerializer):
    start_date = serializers.DateField(required=True)
    end_date = serializers.DateField(required=True)

    class Meta:
        model = LeaveRequest
        fields = (
            'id', 'employee', 'leave_type',
            'start_date', 'end_date', 'reason', 'status',
        )

    def _calculate_leave_days(self, start_date, end_date):
        return (end_date - start_date).days + 1

    def _apply_deduction(self, contract, leave_type, days):
        if leave_type.deduct_from == 'annual':
            contract.annual_leave_days -= days
        elif leave_type.deduct_from == 'sick':
            contract.sick_leave_days -= days
        contract.save()

    def _revert_deduction(self, contract, leave_type, days):
        if leave_type.deduct_from == 'annual':
            contract.annual_leave_days += days
        elif leave_type.deduct_from == 'sick':
            contract.sick_leave_days += days
        contract.save()

    def validate(self, data):
        start_date = data.get('start_date')
        end_date = data.get('end_date')

        if start_date and end_date and start_date >= end_date:
            raise serializers.ValidationError("End date must be after start date.")

        leave_days = (end_date - start_date).days + 1
        if data.get('leave_days') and data['leave_days'] != leave_days:
            raise serializers.ValidationError("Leave days do not match the date range.")

        if not self.instance and data['employee'].leave_requests.filter(is_active=True,
                                                                        status__in=['pending', 'approved'],
                                                                        start_date__lte=end_date,
                                                                        end_date__gte=start_date
                                                                        ).exists():
            raise serializers.ValidationError("Employee already has a leave request in the same date range.")

        leave_type = data['leave_type']
        if leave_type.max_days and leave_days > leave_type.max_days:
            raise serializers.ValidationError(
                f"Leave type has a maximum of {leave_type.max_days} days."
            )

        contract = data['employee'].contract
        if leave_type.deducts_from_allowance:
            if leave_type.deduct_from == 'annual':
                if contract.annual_leave_days < leave_days:
                    raise serializers.ValidationError(
                        f"Insufficient annual leave balance. Available: {contract.annual_leave_days} days"
                    )
            elif leave_type.deduct_from == 'sick':
                if not contract.sick_leave_days:
                    raise serializers.ValidationError("Employee is not eligible for sick leave")
                elif contract.sick_leave_days < leave_days:
                    raise serializers.ValidationError(
                        f"Insufficient sick leave balance. Available: {contract.sick_leave_days} days"
                    )

        return data

    def create(self, validated_data):
        with transaction.atomic():
            request = self.context['request']
            validated_data['created_by'] = request.user
            validated_data['organization'] = request.organization

            leave_days = self._calculate_leave_days(validated_data['start_date'], validated_data['end_date'])
            validated_data['leave_days'] = leave_days

            leave_request = LeaveRequest.objects.create(**validated_data)
            leave_request.leave_id = generate_leave_id(leave_request)
            leave_request.save(update_fields=['leave_id'])
            return leave_request

    def update(self, instance, validated_data):
        with transaction.atomic():
            request = self.context['request']
            instance.updated_by = request.user

            new_start_date = validated_data.get('start_date', instance.start_date)
            new_end_date = validated_data.get('end_date', instance.end_date)
            new_leave_days = self._calculate_leave_days(new_start_date, new_end_date)

            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            instance.leave_days = new_leave_days
            instance.save()

            return instance


class ApproveDeclineLeaveRequestSerializer(serializers.ModelSerializer):
    ACTION_CHOICES = [('approve', 'Approve'), ('decline', 'Decline')]
    action = serializers.ChoiceField(choices=ACTION_CHOICES)
    rejection_reason = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = LeaveRequest
        fields = ['action', 'rejection_reason']

    def validate(self, attrs):
        leave_request = self.instance
        action = attrs.get('action')
        rejection_reason = attrs.get('rejection_reason')

        if leave_request.status != 'pending':
            raise serializers.ValidationError('Only pending leave requests can be approved or declined.')

        if action == 'decline' and not rejection_reason:
            raise serializers.ValidationError({'rejection_reason': 'You need to provide a reason for declining.'})

        return attrs

    def update(self, instance, validated_data):
        with transaction.atomic():
            action = validated_data['action']
            contract = instance.employee.contract

            if action == 'approve':
                if instance.leave_type.deducts_from_allowance:
                    if instance.leave_type.deduct_from == 'annual':
                        if contract.annual_leave_days < instance.leave_days:
                            raise serializers.ValidationError("Not enough annual leave days.")
                        contract.annual_leave_days -= instance.leave_days
                    elif instance.leave_type.deduct_from == 'sick':
                        if not contract.sick_leave_days or contract.sick_leave_days < instance.leave_days:
                            raise serializers.ValidationError("Not enough sick leave days.")
                        contract.sick_leave_days -= instance.leave_days
                    contract.save()
                instance.status = 'approved'
            elif action == 'decline':
                instance.status = 'declined'
                instance.rejection_reason = validated_data.get('rejection_reason', '')
            instance.action_taken_by = self.context['request'].user
            instance.action_taken_on = timezone.now()
            instance.save()
            #todo: Send email notification
            return instance


class FullLeaveRequestSerializer(serializers.ModelSerializer):
    employee = ShortEmployeeSerializer(read_only=True)
    leave_type = LeaveTypeSerializer(read_only=True)
    annual_leave_remaining = serializers.CharField(read_only=True, source='employee.contract.annual_leave_days')
    sick_leave_remaining = serializers.CharField(read_only=True, source='employee.contract.sick_leave_days')
    action_taken_by = ShortUserSerializer(read_only=True)

    class Meta:
        model = LeaveRequest
        fields = (
            'id', 'leave_id', 'employee', 'leave_type', 'start_date', 'end_date',
            'leave_days', 'reason', 'status', 'rejection_reason',
            'annual_leave_remaining', 'sick_leave_remaining', 'date_created',
            'action_taken_by', 'action_taken_on'
        )
