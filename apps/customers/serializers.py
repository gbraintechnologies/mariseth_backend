from rest_framework import serializers

from .models import Customer
from .utils import generate_customer_id
from ..accounts.serializers.users import ShortUserSerializer


class ShortCustomerSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = ('id', 'customer_id', 'name', 'phone_number', 'email')


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
        customer = Customer.objects.create(**validated_data)

        # --- Trigger Manager.io Integration ---
        # This is preferred over signals for its explicitness.
        from apps.shared.models import IntegrationLog
        from apps.shared.tasks.manager_tasks import sync_customer_to_manager

        # Check if a log already exists to prevent duplicates from race conditions.
        if not IntegrationLog.objects.filter(object_id=customer.id, content_type__model='customer').exists():
            log = IntegrationLog.objects.create(content_object=customer, created_by=self.context['request'].user)
            sync_customer_to_manager.delay(log.id)
        # --- End Integration Trigger ---

        return customer

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
