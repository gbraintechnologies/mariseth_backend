from django.db import transaction
from rest_framework import serializers
from django.utils import timezone

from apps.accounts.serializers.users import ShortUserSerializer
from apps.hr.models import Employee, Training, TrainingAttendee
from apps.hr.serializers.employee import ShortEmployeeSerializer
from apps.hr.utils import generate_training_id
from apps.shared.tasks.hr_tasks import send_training_notification


class TrainingAttendeeSerializer(serializers.ModelSerializer):
    employee = ShortEmployeeSerializer(read_only=True)

    class Meta:
        model = TrainingAttendee
        fields = ('id', 'employee', 'status', 'marked_at', 'created_by')
        read_only_fields = ('status', 'marked_at', 'created_by')


class TrainingBaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Training
        fields = (
            'id', 'training_id', 'title', 'description', 'training_type',
            'training_mode', 'start_date', 'end_date', 'location', 'material_url'
        )
        read_only_fields = ('training_id',)


class TrainingSerializer(TrainingBaseSerializer):
    all_employees = serializers.BooleanField(write_only=True, default=False)
    selected_employees = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, allow_empty=True
    )
    departments = serializers.ListField(
        child=serializers.IntegerField(), write_only=True, required=False, allow_empty=True
    )

    class Meta(TrainingBaseSerializer.Meta):
        fields = TrainingBaseSerializer.Meta.fields + ('all_employees', 'selected_employees', 'departments')

    def validate(self, attrs):
        if attrs['start_date'] > attrs['end_date']:
            raise serializers.ValidationError("Start date must be before end date.")
        return attrs

    @transaction.atomic
    def create(self, validated_data):
        request = self.context['request']
        validated_data['created_by'] = request.user
        validated_data['organization'] = request.organization

        all_employees = validated_data.get('all_employees')
        selected_employees = validated_data.pop('selected_employees', [])
        departments = validated_data.pop('departments', [])

        training = Training.objects.create(**validated_data)
        training.training_id = generate_training_id(request.organization.id, training.id)
        training.save(update_fields=['training_id'])

        attendees_to_create = []
        if all_employees:
            employees = Employee.objects.filter(organization=request.organization, is_active=True)
            for employee in employees:
                attendees_to_create.append(
                    TrainingAttendee(training=training, employee=employee, created_by=request.user)
                )
        elif selected_employees:
            for employee_id in selected_employees:
                try:
                    employee = Employee.objects.get(id=employee_id, organization=request.organization, is_active=True)
                    attendees_to_create.append(
                        TrainingAttendee(training=training, employee=employee, created_by=request.user)
                    )
                except Employee.DoesNotExist:
                    raise serializers.ValidationError(f"Employee with ID {employee_id} not found or not active.")
        elif departments:
            employees = Employee.objects.filter(contract__department__in=departments, organization=request.organization,
                                                is_active=True).distinct()
            print(employees)
            for employee in employees:
                attendees_to_create.append(
                    TrainingAttendee(training=training, employee=employee, created_by=request.user)
                )

        if attendees_to_create:
            TrainingAttendee.objects.bulk_create(attendees_to_create)

        send_training_notification.delay(training.id)

        return training

    def update(self, instance, validated_data):
        request = self.context['request']
        instance.updated_by = request.user
        return super().update(instance, validated_data)


class ListTrainingSerializer(TrainingBaseSerializer):
    attendee_count = serializers.IntegerField(read_only=True)
    present_count = serializers.IntegerField(read_only=True)
    attendance_rate = serializers.FloatField(read_only=True)

    class Meta(TrainingBaseSerializer.Meta):
        fields = TrainingBaseSerializer.Meta.fields + (
            'attendee_count', 'present_count', 'attendance_rate', 'date_created'
        )


class FullTrainingSerializer(TrainingBaseSerializer):
    created_by = ShortUserSerializer(read_only=True)
    status = serializers.SerializerMethodField()
    participants = serializers.SerializerMethodField()

    class Meta(TrainingBaseSerializer.Meta):
        fields = TrainingBaseSerializer.Meta.fields + (
            'id', 'training_id', 'description', 'training_type',
            'training_mode', 'start_date', 'end_date', 'location', 'material_url',
            'attendee_count', 'attendance_rate', 'date_created', 'created_by',
            'status', 'participants', 'attendance_status'
        )

    def get_status(self, obj):
        if obj.start_date > timezone.now():
            return 'upcoming'
        elif obj.end_date < timezone.now():
            return 'completed'
        else:
            return 'ongoing'

    def get_participants(self, obj):
        if obj.start_date > timezone.now():
            present_count = "-"
        else:
            present_count = TrainingAttendee.objects.filter(training=obj, status="present").count()
        return f"{present_count}/{obj.attendee_count}"


class ListTrainingAttendeeSerializer(serializers.ModelSerializer):
    training = TrainingSerializer(read_only=True)

    class Meta:
        model = TrainingAttendee
        fields = (
            'id', 'training',  'status',
            'marked_at', 'created_by', 'date_created'
        )
