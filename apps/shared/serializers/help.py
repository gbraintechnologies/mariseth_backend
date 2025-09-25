from rest_framework import serializers

from apps.accounts.serializers.users import ShortUserSerializer
from apps.shared.models import Help


class HelpSerializer(serializers.ModelSerializer):
    class Meta:
        model = Help
        fields = ('id', 'title', 'description', 'url')
        read_only_fields = ('id',)

    def create(self, validated_data):
        request = self.context['request']
        created_by = request.user
        organization = validated_data.pop('organization')
        return Help.objects.create(created_by=created_by, organization=organization, **validated_data)

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.updated_by = self.context['request'].user
        instance.save()
        return instance


class FullHelpSerializer(serializers.ModelSerializer):
    created_by = ShortUserSerializer()

    class Meta:
        model = Help
        fields = ('id', 'title', 'description', 'url', 'created_by', 'date_created')
        read_only_fields = ('id', 'created_by', 'date_created')