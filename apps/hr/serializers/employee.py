from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.hr.models import Employee, EmployeeContract, EmployeeDisciplinaryAction, EmployeeEmergencyContact, \
    EmployeeQualification
from apps.hr.serializers.department import FullDepartmentSerializer
from apps.hr.serializers.job_title import FullJobTitleSerializer
from apps.hr.utils import generate_employee_id


class ShortEmployeeSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ('id', 'first_name', 'last_name', 'employee_id')
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
            'id', 'start_date', 'job_title',
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

    class Meta:
        model = Employee
        fields = (
            'id', 'employee_id', 'first_name', 'last_name',
            'gender', 'relationship_status', 'email', 'phone_number',
            'date_of_birth', 'bank_account_number', 'status',
            'emergency_contacts', 'qualifications', 'contract'
        )
        read_only_fields = ('employee_id',)

    def create(self, validated_data):
        request = self.context['request']
        validated_data['created_by'] = request.user
        validated_data['organization'] = request.organization
        emergency_contacts_data = validated_data.pop('emergency_contacts', [])
        qualifications_data = validated_data.pop('qualifications', [])
        contract_data = validated_data.pop('contract', {})

        employee = Employee.objects.create(**validated_data)
        employee.employee_id = generate_employee_id(request.organization.id, employee.id)
        employee.save()

        for contact_data in emergency_contacts_data:
            EmployeeEmergencyContact.objects.create(employee=employee, **contact_data)

        for qualification_data in qualifications_data:
            EmployeeQualification.objects.create(employee=employee, **qualification_data)

        if contract_data:
            EmployeeContract.objects.create(employee=employee, **contract_data)

        return employee

    def update(self, instance, validated_data):
        request = self.context['request']
        emergency_contacts_data = validated_data.pop('emergency_contacts', None)
        qualifications_data = validated_data.pop('qualifications', None)
        contract_data = validated_data.pop('contract', None)

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
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
            'id', 'start_date', 'job_title',
            'department', 'employment_type', 'work_type',
            'annual_leave_days', 'sick_leave_days', 'leave_rollover'
        )


class FullEmployeeSerializer(serializers.ModelSerializer):
    created_by = ShortUserSerializer(read_only=True)
    emergency_contacts = EmergencyContactSerializer(many=True, read_only=True)
    qualifications = serializers.SerializerMethodField()
    contract = FullEmployeeContractSerializer(read_only=True)

    class Meta:
        model = Employee
        fields = (
            'id', 'employee_id', 'first_name', 'last_name', 'gender',
            'relationship_status', 'email', 'phone_number', 'bank_account_number',
            'status', 'date_of_birth', 'emergency_contacts',
            'qualifications', 'contract', 'created_by', 'date_created',
        )
        read_only_fields = ('id', 'employee_id', 'created_by', 'date_created', 'updated_by', 'date_updated')

    def get_qualifications(self, obj):
        return QualificationSerializer(obj.qualifications.filter(is_active=True), many=True).data


class ListEmployeeSerializer(serializers.ModelSerializer):
    job_title = serializers.CharField(source='contract.job_title.name', read_only=True)
    department = serializers.CharField(source='contract.department.name', read_only=True)
    work_location = serializers.CharField(source='contract.work_location', read_only=True)

    class Meta:
        model = Employee
        fields = (
            'id', 'employee_id', 'first_name', 'last_name', 'gender',
            'relationship_status', 'email', 'phone_number', 'bank_account_number',
            'status', 'date_of_birth', 'date_created',
            'job_title', 'department', 'work_location'
        )
