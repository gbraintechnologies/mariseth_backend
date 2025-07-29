import random

from django.db import transaction
from rest_framework import serializers

from apps.accounts.models import User
from apps.farm.models import Farmer
from apps.farm.serializers.farmer import FullFarmerSerializer
from apps.organizations.models import OrganizationUser
from apps.shared.literals import ACCESS_TOKEN, REFRESH_TOKEN
from apps.shared.tasks.sms_tasks import send_verification_sms
from apps.shared.utils.helpers import authenticate, generate_tokens
from apps.shared.utils.validators import validate_only_digits


class MobileRegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, validators=[validate_only_digits])

    def validate_phone_number(self, value):
        if not Farmer.objects.filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number is not registered as a farmer")

        user = User.objects.filter(phone_number=value).first()
        if user and user.is_verified:
            raise serializers.ValidationError("User already registered")

        return value

    def create(self, validated_data):
        phone_number = validated_data['phone_number']
        farmer = Farmer.objects.get(phone_number=phone_number)
        user, created = User.objects.update_or_create(
            phone_number=phone_number,
            defaults={
                'username': phone_number,
                'email': farmer.email or f"{phone_number}@marisethfarms.com",
                'first_name': farmer.first_name,
                'last_name': farmer.last_name,
                'is_active': True,
                'is_verified': False,
                'user_type': 'user',
                'status': 'active'
            }
        )
        farmer.user = user
        farmer.save()
        organization_user, created = OrganizationUser.objects.update_or_create(
            user=user,
            organization=farmer.organization
        )
        verification_code = random.randint(1000, 9999)
        user.verification_code = verification_code
        user.save()
        transaction.on_commit(
            lambda: send_verification_sms.delay(
                user_id=user.id,
                phone_number=phone_number,
                verification_code=verification_code
            )
        )

        return user


class SetPinSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20)
    pin = serializers.CharField(min_length=4, max_length=4, validators=[validate_only_digits], write_only=True)

    def validate(self, attrs):
        user = User.objects.get(phone_number=attrs['phone_number'], is_active=True)
        if not user:
            raise serializers.ValidationError("User not found")

        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        user = validated_data['user']
        user.set_password(validated_data['pin'])
        user.save()
        return user


class MobileLoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, validators=[validate_only_digits])
    pin = serializers.CharField(min_length=4, max_length=4, write_only=True, validators=[validate_only_digits])

    def validate(self, attrs):
        user = authenticate(phone_number=attrs['phone_number'], pin=attrs['pin'])
        if user is None or not user.is_active:
            raise serializers.ValidationError("Invalid phone number or pin")
        if not user.is_verified:
            raise serializers.ValidationError("User is not verified")
        if not user.organization_users.exists():
            raise serializers.ValidationError("User is not associated with an organization")
        attrs['user'] = user
        return attrs


class MobileUserWithTokenAndFarmerSerializer(serializers.ModelSerializer):
    farmer = FullFarmerSerializer(read_only=True)
    access_token = serializers.CharField(read_only=True)
    refresh_token = serializers.CharField(read_only=True)

    class Meta:
        model = User
        fields = [
            'id', 'email', 'phone_number', 'first_name',
            'last_name', 'is_verified', 'user_type', 'status',
            'user_type', 'farmer', 'access_token', 'refresh_token',
        ]

    def to_representation(self, user):
        ret = super().to_representation(user)

        tokens = generate_tokens(user)

        ret[ACCESS_TOKEN] = tokens['access_token']
        ret[REFRESH_TOKEN] = tokens['refresh_token']

        return ret


class UpdateAccount(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name',
            'phone_number', 'avatar', 'gender', 'email',
            'user_type'
        ]


class MobileAccountVerificationSerializer(serializers.Serializer):
    code = serializers.IntegerField(required=True)
    phone_number = serializers.CharField(max_length=20, validators=[validate_only_digits])

    def validate(self, attrs):
        phone_number = attrs['phone_number']
        code = attrs['code']

        user = User.objects.filter(phone_number=phone_number, is_active=True).first()
        # consider blocking already verified users
        if not user:
            raise serializers.ValidationError("User not found")
        if user.verification_code != code:
            raise serializers.ValidationError("Invalid verification code")

        attrs['user'] = user
        return attrs

    def create(self, validated_data):
        verification_code = validated_data["code"]
        phone_number = validated_data['phone_number']
        user = User.objects.get(
            phone_number=phone_number, verification_code=verification_code, is_active=True)
        user.set_is_verified()
        user.save()

        return user


class MobileResendVerificationCodeSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, validators=[validate_only_digits])

    def create(self, validated_data):
        phone_number = validated_data["phone_number"]

        try:
            user = User.objects.get(phone_number=phone_number, is_active=True)
            verification_code = random.randint(1000, 9999)
            user.verification_code = verification_code
            user.save()
            send_verification_sms.delay(
                user_id=user.id,
                phone_number=phone_number,
                verification_code=verification_code
            )

        except User.DoesNotExist:
            raise serializers.ValidationError(
                'User with this email does not exist or is not active')

        return user


class MobileUpdatePinSerializer(serializers.Serializer):
    old_pin = serializers.CharField(required=True)
    new_pin = serializers.CharField(required=True)

    def validate(self, attrs):
        user = self.instance
        if user.check_password(attrs.get("old_pin")):
            return attrs
        raise serializers.ValidationError("The old password is invalid")

    def update(self, instance, validated_data):
        instance.set_password(validated_data["new_pin"])
        instance.save()
        return instance


class MobileResetPasswordSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=20, validators=[validate_only_digits])
    code = serializers.IntegerField(required=True)
    new_pin = serializers.CharField(required=True)

    def validate(self, validated_data):
        phone_number = validated_data["phone_number"]
        verification_code = validated_data["code"]

        try:
            user = User.objects.get(
                phone_number=phone_number,
                verification_code=verification_code,
                is_active=True
            )
            validated_data['user'] = user
            return validated_data
        except User.DoesNotExist:
            raise serializers.ValidationError("Invalid email or verification code")

    def create(self, validated_data):
        user = validated_data['user']
        new_password = validated_data["new_pin"]
        user.set_password(new_password)
        user.set_is_verified()
        user.save()

        return user


class MobileUpdateAccount(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'first_name', 'last_name',
            'phone_number', 'avatar', 'gender', 'email',
        ]
        # TODO: ADD FUNCTION TO UPDATE FARMER INFORMATION
