from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from django.db import transaction

from apps.accounts.serializers.users import GroupSerializer
from apps.organizations.models import OrganizationUser
from apps.organizations.serializers.organization import ShortOrganizationSerializer
from apps.shared.general_response import INVALID_LOGIN
from apps.shared.literals import ACCESS_TOKEN, EMAIL, FORGOTTEN_PASSWORD_EMAIL_TEMPLATE, NEW_PASSWORD, OLD_PASSWORD, \
    REFRESH_TOKEN, VERIFICATION_CODE, VERIFICATION_EMAIL_TEMPLATE
from apps.shared.tasks.email_tasks import send_verification_email
from apps.shared.utils.helpers import generate_tokens

User = get_user_model()


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    password = serializers.CharField(required=True)

    def validate(self, attrs):
        user = authenticate(**attrs)
        if user is None or not user.is_active:
            raise serializers.ValidationError(INVALID_LOGIN)
        if not user.organization_users.exists():
            raise serializers.ValidationError("User is not associated with an organization")
        attrs['user'] = user
        return attrs


class UserWithTokenSerializer(serializers.ModelSerializer):
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)
    groups = GroupSerializer(many=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'gender', 'first_name', 'last_name',
            'access_token', 'refresh_token', 'avatar','user_type',
        ]

    def to_representation(self, user):
        ret = super().to_representation(user)

        tokens = generate_tokens(user)

        ret[ACCESS_TOKEN] = tokens['access_token']
        ret[REFRESH_TOKEN] = tokens['refresh_token']
        org_user = OrganizationUser.objects.select_related('organization').get(user=user)
        ret['organization'] = ShortOrganizationSerializer(
            org_user.organization).data

        return ret


class LogoutSerializer(serializers.Serializer):
    refresh_token = serializers.CharField(required=True)

    def create(self, validated_data):
        token = RefreshToken(validated_data[REFRESH_TOKEN])
        token.blacklist()
        return token

    def validate_refresh_token(self, val):
        try:
            RefreshToken(val)
        except TokenError:
            raise serializers.ValidationError('Refresh token is blacklisted and cannot be used. '
                                              'Try login instead to get a new refresh token')


class AccountVerificationSerializer(serializers.Serializer):
    verification_code = serializers.IntegerField()
    email = serializers.EmailField(required=True)

    def create(self, validated_data):
        verification_code = validated_data[VERIFICATION_CODE]
        email = validated_data[EMAIL]

        try:
            user = User.objects.get(
                email=email, verification_code=verification_code, is_active=True)
            user.set_is_verified()
            user.save()

        except User.DoesNotExist:
            raise serializers.ValidationError(
                'Invalid Email or Verification code')

        return user


class ResendVerificationCodeSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def create(self, validated_data):
        email = validated_data[EMAIL]

        try:
            user = User.objects.get(email=email, is_active=True)
            code = user.set_email_verification_code()
            template_name = VERIFICATION_EMAIL_TEMPLATE
            user.save()
            transaction.on_commit(
                lambda: send_verification_email.delay(
                    code, template_name=template_name, user_id=user.id
                )
            )

        except User.DoesNotExist:
            raise serializers.ValidationError(
                'User with this email does not exist or is not active')

        return user


class UpdateAccount(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            'id', 'first_name', 'last_name',
            'phone_number', 'avatar', 'gender', 'email',
            'user_type'
        ]


class UpdatePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True)

    def validate(self, attrs):
        user = self.instance
        if user.check_password(attrs.get(OLD_PASSWORD)):
            return attrs
        raise serializers.ValidationError("The old password is invalid")

    def update(self, instance, validated_data):
        instance.set_password(validated_data[NEW_PASSWORD])
        instance.save()
        return instance


class ForgotPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)

    def create(self, validated_data):
        email = validated_data[EMAIL]

        try:
            user = User.objects.get(email=email, is_active=True)
            code = user.set_email_verification_code()
            template_name = FORGOTTEN_PASSWORD_EMAIL_TEMPLATE
            user.save()

            transaction.on_commit(
                lambda: send_verification_email.delay(
                    code, template_name=template_name, user_id=user.id
                )
            )
        except User.DoesNotExist:
            raise serializers.ValidationError(
                'User with this email does not exist')

        return user


class ResetPasswordSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    verification_code = serializers.IntegerField(required=True)
    new_password = serializers.CharField(required=True)

    def validate(self, validated_data):
        email = validated_data[EMAIL]
        verification_code = validated_data[VERIFICATION_CODE]

        try:
            user = User.objects.get(
                email=email,
                verification_code=verification_code,
                is_active=True
            )
            validated_data['user'] = user
            return validated_data
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or verification code")

    def create(self, validated_data):
        user = validated_data['user']
        new_password = validated_data[NEW_PASSWORD]
        user.set_password(new_password)
        user.set_is_verified()
        user.save()

        return user
