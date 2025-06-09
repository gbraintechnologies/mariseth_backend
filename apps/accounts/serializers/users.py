from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.core.exceptions import ValidationError
from rest_framework import serializers

from apps.accounts.models import AppGroup, AppPermission
from apps.organizations.models import Organization, OrganizationUser
from apps.organizations.serializers.organization import ShortOrganizationSerializer
from apps.shared.literals import VERIFICATION_EMAIL_TEMPLATE
from apps.shared.tasks.email_tasks import send_verification_email

User = get_user_model()
ENVIRONMENT = settings.ENVIRONMENT


class ShortUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'email', 'first_name', 'username', 'last_name',
            'gender', 'phone_number', 'avatar', 'date_created',
            'user_type'
        ]


class NewUserSerializer(serializers.ModelSerializer):
    group = serializers.PrimaryKeyRelatedField(queryset=AppGroup.objects.all(), required=True)
    organization = serializers.PrimaryKeyRelatedField(queryset=Organization.objects.all(), required=False)
    avatar = serializers.ImageField(required=False)
    user_type = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'email', 'first_name', 'username', 'last_name',
            'gender', 'phone_number', 'avatar', 'group',
            'organization', 'user_type', "avatar"
        ]

    def validate(self, data):
        request = self.context.get('request')
        organization = request.organization
        group = data.get('group')

        if group:
            if not (group.is_default or group.organization == organization):
                raise serializers.ValidationError(
                    f"The group does not belong to your organization."
                )
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        group = validated_data.pop('group', None)
        organization = request.organization
        validated_data["user_type"] = "admin"
        # Create the user
        user = User(**validated_data)
        code = user.set_email_verification_code()
        user.save()
        send_verification_email.delay(
            code, template_name=VERIFICATION_EMAIL_TEMPLATE, user=user.id
        )
        organization_user = OrganizationUser.objects.create(
            user=user,
            organization=organization,
        )
        if group:
            user.groups.set([group])

        return user

    def update(self, instance, validated_data):
        new_group = validated_data.pop('group', None)
        current_group = instance.groups.first()
        if new_group is not None and current_group != new_group:
            instance.groups.clear()
            instance.groups.set([new_group])

        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()

        return instance


class PermissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Permission
        fields = ['id', 'name', 'codename']


class GroupSerializer(serializers.ModelSerializer):
    is_default = serializers.ReadOnlyField()
    permissions = serializers.SerializerMethodField()

    class Meta:
        model = AppGroup
        fields = ['id', 'name', 'rank', 'permissions', 'is_default', 'description']

    def to_representation(self, instance):
        """
        Conditionally include users based on 'include_users' query parameter.
        """
        representation = super().to_representation(instance)

        request = self.context.get('request')
        if request and 'include_users' in request.query_params:
            representation['users'] = ShortUserSerializer(instance.user_set.filter(is_active=True), many=True).data

        return representation

    def get_permissions(self, obj):
        permissions = obj.permissions.order_by('codename')
        if AppGroup.objects.get_super_admin_group() == obj:
            permissions = AppPermission.objects.get_permissions()

        data = PermissionSerializer(
            permissions, many=True
        ).data
        return data


class GroupWithRankSerializer(serializers.ModelSerializer):
    is_default = serializers.ReadOnlyField()

    class Meta:
        model = AppGroup
        fields = ['id', 'name', 'rank', 'permissions', 'is_default', 'description']

    def validate(self, validated_data):
        request = self.context.get('request', None)
        if request:
            validated_data['organization'] = request.organization

        return validated_data

    def create(self, validated_data):
        permissions = validated_data.pop('permissions', [])
        group = AppGroup(**validated_data)
        try:
            group.full_clean()
            group.save()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

        if permissions:
            group.permissions.set(permissions)
        return group

    def update(self, instance, validated_data):
        permissions = validated_data.pop('permissions', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        try:
            instance.full_clean()
            instance.save()
        except ValidationError as e:
            raise serializers.ValidationError(e.message_dict)

        if permissions is not None:
            instance.permissions.set(permissions)
        return instance


class UserSerializer(serializers.ModelSerializer):
    groups = GroupSerializer(many=True)
    organization = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = [
            'id', 'username', 'first_name', 'last_name',
            'email', 'gender', 'phone_number', 'is_verified',
            'avatar', 'groups', 'organization',
        ]

    def get_organization(self, obj):
        try:
            organization_user = OrganizationUser.objects.get(user=obj)
            return ShortOrganizationSerializer(organization_user.get_user_organization()).data
        except OrganizationUser.DoesNotExist:
            return None
