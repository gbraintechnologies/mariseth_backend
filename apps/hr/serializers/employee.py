from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from apps.accounts.serializers.users import ShortUserSerializer
from apps.hr.models import Employee, EmployeeContract, EmployeeDisciplinaryAction, EmployeeEmergencyContact,     EmployeeQualification, LeaveRequest, LeaveType
from apps.hr.serializers.department import FullDepartmentSerializer
from apps.hr.serializers.job_title import FullJobTitleSerializer
from apps.hr.utils import generate_employee_id
from apps.shared.utils.helpers import base64_to_image


class ShortEmployeeSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(read_only=True, source='contract.job_title.name')
    department = serializers.CharField(read_only=True, source='contract.department.name')

    class Meta:
        model = Employee
        fields = ('id', 'first_name', 'last_name', 'employee_id',
                  'email', 'phone_number', 'job_title', 'department')
        read_only_fields = ('id',)


class EmergencyContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeEmergencyContact
        fields = ('id', 'name', 'relationship', 'phone_number')


class QualificationSerializer(serializers.ModelSerializer):
    certificate = serializers.FileField(required=False, allow_null=True)

    class Meta:
        model = EmployeeQualification
        fields = ('id', 'title', 'description', 'certificate')


class EmployeeContractSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeContract
        fields = (
            'id', 'start_date', 'ssnit_number', 'bank_name',
            'bank_branch', 'account_number', 'job_title',
            'department', 'employment_type', 'work_type',
            'annual_leave_days', 'sick_leave_days', 'leave_rollover'
        )


class DisciplinaryActionSerializer(serializers.ModelSerializer):
    class Meta:
        model = EmployeeDisciplinaryAction
        fields = ('id', 'action_type', 'offence', 'date_issued', 'comments')
        read_only_fields = ('employee', 'date_created')

    def create(self, validated_data):
        request = self.context['request']
        employee = request.data['employee']
        disciplinary_action = super().create(validated_data)
        if disciplinary_action.action_type == 'suspension':
            employee.status = 'suspended'
        elif disciplinary_action.action_type == 'dismissal':
            employee.status = 'inactive'
        employee.save()
        return disciplinary_action


class EmployeeSerializer(serializers.ModelSerializer):
    emergency_contacts = EmergencyContactSerializer(many=True, required=False)
    qualifications = QualificationSerializer(many=True, required=False)
    contract = EmployeeContractSerializer(required=False)
    profile_picture = serializers.CharField(write_only=True, required=False, allow_blank=True)

    class Meta:
        model = Employee
        fields = (
            'id', 'employee_id', 'first_name', 'last_name',
            'gender', 'relationship_status', 'email', 'phone_number',
            'date_of_birth', 'bank_account_number', 'status',
            'emergency_contacts', 'qualifications', 'contract',
            'notification', 'ghana_card_number', 'profile_picture'
        )
        read_only_fields = ('employee_id',)

    def create(self, validated_data):
        request = self.context['request']
        validated_data['created_by'] = request.user
        validated_data['organization'] = request.organization
        emergency_contacts_data = validated_data.pop('emergency_contacts', [])
        qualifications_data = validated_data.pop('qualifications', [])
        contract_data = validated_data.pop('contract', {})
        profile_picture_data = validated_data.pop('profile_picture', None)

        employee = Employee.objects.create(**validated_data)
        employee.employee_id = generate_employee_id(request.organization.id, employee.id)
        
        if profile_picture_data:
            employee.profile_picture = base64_to_image(profile_picture_data)

        employee.save()

        for contact_data in emergency_contacts_data:
            EmployeeEmergencyContact.objects.create(employee=employee, **contact_data)

        for qualification_data in qualifications_data:
            EmployeeQualification.objects.create(employee=employee, **qualification_data)

        if contract_data:
            EmployeeContract.objects.create(employee=employee, **contract_data)

        # --- Trigger Manager.io Integration ---
        from apps.shared.models import IntegrationLog
        from apps.shared.tasks.manager_tasks import sync_employee_to_manager

        if not IntegrationLog.objects.filter(object_id=employee.id, content_type__model='employee').exists():
            log = IntegrationLog.objects.create(content_object=employee, created_by=request.user)
            sync_employee_to_manager.delay(log.id)
        # --- End Integration Trigger ---

        return employee

    def update(self, instance, validated_data):
        request = self.context['request']
        emergency_contacts_data = validated_data.pop('emergency_contacts', None)
        qualifications_data = validated_data.pop('qualifications', None)
        contract_data = validated_data.pop('contract', None)
        profile_picture_data = validated_data.pop('profile_picture', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if profile_picture_data:
            instance.profile_picture = base64_to_image(profile_picture_data)

        instance.updated_by = request.user
        instance.save()

        if emergency_contacts_data is not None:
            instance.emergency_contacts.all().delete()
            for contact_data in emergency_contacts_data:
                EmployeeEmergencyContact.objects.create(employee=instance, **contact_data)

        if qualifications_data is not None:
            instance.qualifications.all().delete()
            for qualification_data in qualifications_data:
                EmployeeQualification.objects.create(employee=instance, **qualification_data)

        if contract_data is not None:
            if hasattr(instance, 'contract'):
                contract_serializer = self.fields['contract']
                contract_instance = instance.contract
                contract_serializer.update(contract_instance, contract_data)
            else:
                EmployeeContract.objects.create(employee=instance, **contract_data)

        return instance


class FullEmployeeContractSerializer(serializers.ModelSerializer):
    job_title = FullJobTitleSerializer(read_only=True)
    department = FullDepartmentSerializer(read_only=True)

    class Meta:
        model = EmployeeContract
        fields = (
            'id', 'start_date', 'ssnit_number', 'bank_name',
            'bank_branch', 'account_number', 'job_title',
            'department', 'employment_type', 'work_type',
            'annual_leave_days', 'sick_leave_days', 'leave_rollover'
        )


class FullEmployeeSerializer(serializers.ModelSerializer):
    created_by = ShortUserSerializer(read_only=True)
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    qualifications = serializers.SerializerMethodField()
    contract = FullEmployeeContractSerializer(read_only=True)
    leave_days_left = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(read_only=True)

    class Meta:
        model = Employee
        fields = (
            'id', 'employee_id', 'first_name', 'last_name', 'gender',
            'relationship_status', 'email', 'phone_number', 'bank_account_number',
            'status', 'date_of_birth', 'emergency_contacts', 'notification',
            'qualifications', 'contract', 'created_by', 'date_created',
            'leave_days_left', 'ghana_card_number', 'profile_picture'
        )
        read_only_fields = ('id', 'employee_id', 'created_by', 'date_created', 'updated_by', 'date_updated')

    def get_qualifications(self, obj):
        return QualificationSerializer(obj.qualifications.filter(is_active=True), many=True).data

    def get_leave_days_left(self, obj):
        if not hasattr(obj, 'contract'):
            return {'annual': 0, 'sick': 0}

        annual_allowance = obj.contract.annual_leave_days
        sick_allowance = obj.contract.sick_leave_days

        approved_leave_requests = obj.leave_requests.filter(status='approved')

        for lr in approved_leave_requests:
            if lr.leave_type.deducts_from_allowance:
                if lr.leave_type.deduct_from == 'annual':
                    annual_allowance -= lr.leave_days
                elif lr.leave_type.deduct_from == 'sick':
                    sick_allowance -= lr.leave_days

        return {'annual': max(0, annual_allowance), 'sick': max(0, sick_allowance)}


class ListEmployeeSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='contract.job_title.name', read_only=True)
    department = serializers.CharField(source='contract.department.name', read_only=True)
    work_location = serializers.CharField(source='contract.work_location', read_only=True)
    annual_leave_days_left = serializers.SerializerMethodField()
    sick_leave_days_left = serializers.SerializerMethodField()
    profile_picture = serializers.ImageField(read_only=True)

    class Meta:
        model = Employee
        fields = (
            'id', 'employee_id', 'first_name', 'last_name', 'gender',
            'relationship_status', 'email', 'phone_number', 'bank_account_number',
            'status', 'date_of_birth', 'date_created',
            'job_title', 'department', 'work_location',  'profile_picture',
            'annual_leave_days_left', 'sick_leave_days_left'
        )

    def get_annual_leave_days_left(self, obj):
        if not hasattr(obj, 'contract'):
            return 0

        annual_allowance = obj.contract.annual_leave_days
        approved_leave_requests = obj.leave_requests.filter(status='approved')

        for lr in approved_leave_requests:
            if lr.leave_type.deducts_from_allowance and lr.leave_type.deduct_from == 'annual':
                annual_allowance -= lr.leave_days
        return max(0, annual_allowance)

    def get_sick_leave_days_left(self, obj):
        if not hasattr(obj, 'contract'):
            return 0

        sick_allowance = obj.contract.sick_leave_days
        approved_leave_requests = obj.leave_requests.filter(status='approved')

        for lr in approved_leave_requests:
            if lr.leave_type.deducts_from_allowance and lr.leave_type.deduct_from == 'sick':
                sick_allowance -= lr.leave_days
        return max(0, sick_allowance)


class EmployeeExportSerializer(serializers.ModelSerializer):
    department = serializers.CharField(source='contract.department.name', read_only=True)
    job_title = serializers.CharField(source='contract.job_title.name', read_only=True)
    gender = serializers.CharField(source='get_gender_display', read_only=True)
    status = serializers.CharField(source='get_status_display', read_only=True)
    employment_type = serializers.CharField(source='contract.get_employment_type_display', read_only=True)
    work_type = serializers.CharField(source='contract.get_work_type_display', read_only=True)
    relationship_status = serializers.CharField(source='get_relationship_status_display', read_only=True)

    class Meta:
        model = Employee
        fields = (
            'employee_id', 'first_name', 'last_name', 'gender',
            'relationship_status', 'email', 'phone_number', 'date_of_birth',
            'bank_account_number', 'status', 'department', 'job_title',
            'employment_type', 'work_type'
        )
