from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.hr.models import Department, JobTitle
from apps.hr.serializers.department import DepartmentSerializer
from apps.hr.utils import generate_job_title_id
from apps.shared.models import CustomType
from apps.shared.serializers.custom_types import CustomTypeSerializer


class JobTitleSerializer(serializers.ModelSerializer):
    department = serializers.PrimaryKeyRelatedField(
        queryset=Department.objects.filter(is_active=True), write_only=True
    )
    level = serializers.PrimaryKeyRelatedField(
        queryset=CustomType.objects.filter(is_active=True), allow_null=True, required=False
    )

    class Meta:
        model = JobTitle
        fields = (
            "id", "name", "level", "department",
            "job_description_url", "job_title_id",
            "probation"
        )

    def create(self, validated_data):
        request = self.context.get('request')
        organization = request.organization
        validated_data['organization'] = organization
        validated_data['created_by'] = self.context['request'].user
        job_title = JobTitle.objects.create(**validated_data)
        job_title.job_title_id = generate_job_title_id(organization.id, job_title.pk)
        job_title.save()
        return job_title

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class FullJobTitleSerializer(serializers.ModelSerializer):
    department = DepartmentSerializer(read_only=True)
    level = CustomTypeSerializer(read_only=True)
    created_by = ShortUserSerializer(read_only=True)
    number_of_employees = serializers.SerializerMethodField()

    class Meta:
        model = JobTitle
        fields = (
            "id", "name", "level", "department",
            "job_description_url", "job_title_id",
            "probation", 'date_created', 'created_by',
            "number_of_employees"
        )

    def get_number_of_employees(self, obj):
        return obj.employees.count()
