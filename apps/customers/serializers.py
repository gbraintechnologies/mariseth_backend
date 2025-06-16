from rest_framework import serializers

from .models import Customer
from .utils import generate_customer_id
from ..accounts.serializers.users import ShortUserSerializer


class CustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = (
            'id', 'name', 'phone_number', 'email',
            'location', 'company', 'comments',
            'date_created',
        )
        read_only_fields = ('id', 'date_created',)

    def create(self, validated_data):
        validated_data['created_by'] = self.context['request'].user
        validated_data['organization'] = self.context['request'].organization
        validated_data['customer_id'] = generate_customer_id(self.context['request'].organization.id)
        return Customer.objects.create(**validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance


class FullCustomerSerializer(serializers.ModelSerializer):
    created_by = ShortUserSerializer(read_only=True)

    class Meta:
        model = Customer
        fields = (
            'id', 'customer_id', 'name', 'phone_number', 'email',
            'location', 'company', 'comments', 'date_created', 'created_by'
        )
