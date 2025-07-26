from rest_framework import serializers

from apps.hr.models import Department
from apps.hr.utils import generate_department_id


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = (
            "id", "name", "description", "department_id", "status"
        )

    def create(self, validated_data):
        request = self.context['request']
        organization = request.organization
        validated_data['organization'] = organization
        department = Department.objects.create(**validated_data)
        department.department_id = generate_department_id(organization.id, department.pk)
        department.save()
        return department

    def update(self, instance, validated_data):
        print(validated_data)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class FullDepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = (
            "id", "name", "description", "department_id", "status"
        )
