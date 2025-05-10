from django.db.models import Q
from rest_framework import serializers

from apps.shared.models import CustomType


class CustomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomType
        fields = ['id', 'name', 'category_name', 'description', 'category_type', 'is_default']

    def validate_name(self, value):
        if self.instance and self.instance.name == value:
            return value
        organization = self.context['request'].organization
        query = Q(name=value, organization=organization) | Q(is_default=True, name=value)
        if self.instance:
            query &= ~Q(id=self.instance.id)
        if CustomType.objects.filter(query).exists():
            raise serializers.ValidationError("Name already exists")

        return value

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['organization'] = request.organization
        validated_data['created_by'] = self.context['request'].user
        custom_type = CustomType.objects.create(**validated_data)
        return custom_type

    def update(self, instance, validated_data):
        instance.name = validated_data.get('name', instance.name)
        instance.category_name = validated_data.get('category_name', instance.category_name)
        instance.description = validated_data.get('description', instance.description)
        instance.category_type = validated_data.get('category_type', instance.category_type)
        instance.save()
        return instance
