from rest_framework import serializers

from apps.shared.models import AppSetting


class AppSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = AppSetting
        fields = ['id', 'config']

    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['organization'] = request.organization
        validated_data['created_by'] = self.context['request'].user
        app_setting = AppSetting.objects.create(**validated_data)
        return app_setting

    def update(self, instance, validated_data):
        instance.share_pricing = validated_data.get('share_pricing', instance.share_pricing)
        instance.tax_value = validated_data.get('tax_value', instance.tax_value)
        instance.config = validated_data.get('config', instance.config)
        instance.save()
        return instance
