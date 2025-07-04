from django.contrib.auth import get_user_model, logout as user_logout
from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response

from apps.accounts.serializers.auth import LogoutSerializer
from apps.consuner_mobile.serializers.auth import MobileAccountVerificationSerializer, MobileLoginSerializer, \
    MobileRegisterSerializer, MobileResendVerificationCodeSerializer, \
    MobileResetPasswordSerializer, MobileUpdateAccount, MobileUpdatePinSerializer, \
    MobileUserWithTokenAndFarmerSerializer, SetPinSerializer
from apps.consuner_mobile.swagger import add_swagger_to_mobile_user_auth_viewset
from apps.farm.serializers.farmer import FarmerSerializer, FullFarmerSerializer
from apps.shared.general_response import GENERAL_SUCCESS_RESPONSE

User = get_user_model()


@add_swagger_to_mobile_user_auth_viewset
class MobileUserAuthViewSet(viewsets.GenericViewSet):
    serializer_class = MobileUserWithTokenAndFarmerSerializer
    queryset = User.objects.filter(is_active=True)

    def get_permissions(self):
        if self.action in ["update_password", "update_account", 'logout', 'me']:
            return [IsAuthenticated()]
        return [AllowAny()]

    @action(detail=False, methods=['POST'])
    def login(self, request):
        serializer = MobileLoginSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.validated_data['user']
            if user is not None:
                return Response(MobileUserWithTokenAndFarmerSerializer(user).data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['POST'])
    @transaction.atomic
    def register(self, request):
        serializer = MobileRegisterSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(
                {"message": "Registration successful a code has been sent to your phone number for verification"},
                status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'], url_path='verify-phone')
    @transaction.atomic
    def verify_phone(self, request):
        serializer = MobileAccountVerificationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response({"message": "Verification successful, setup your pin"}, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'], url_path='setup-pin')
    @transaction.atomic
    def set_pin(self, request):
        """Set PIN for new registration or password reset"""
        serializer = SetPinSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        user = serializer.save()
        return Response(MobileUserWithTokenAndFarmerSerializer(user).data, status=status.HTTP_200_OK)

    @action(detail=False, methods=['POST'])
    def logout(self, request):
        serializer = LogoutSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            user_logout(request)
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['PATCH'], url_path='update-pin')
    @transaction.atomic
    def update_pin(self, request, pk=None):
        user = self.request.user
        serializer = MobileUpdatePinSerializer(instance=user, data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_401_UNAUTHORIZED)

    @action(detail=False, methods=['PUT'], url_path='update-account')
    @transaction.atomic
    def update_account(self, request):
        serializer = MobileUpdateAccount(self.request.user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'], url_path='resend-verification-code')
    @transaction.atomic
    def resend_verification_code(self, request):
        """
        Resend verification code
        """
        serializer = MobileResendVerificationCodeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'], url_path='forgot-password')
    def forgot_password(self, request):
        """
        Forgot Password
        """
        serializer = MobileResendVerificationCodeSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['POST'], url_path='reset-password')
    def reset_password(self, request):
        """
        Reset Password
        """
        serializer = MobileResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(GENERAL_SUCCESS_RESPONSE, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['PUT'], url_path='update-my-farmer')
    @transaction.atomic
    def update_my_farmer(self, request):
        farmer = request.user.farmer
        mutable_data = request.data.copy()
        for restricted_field in ['type', 'farm', 'lead_farmer', 'phone_number']:
            mutable_data.pop(restricted_field, None)

        serializer = FarmerSerializer(instance=farmer, data=mutable_data, partial=True, context={'request': request})
        if serializer.is_valid():
            serializer.save()

            user = farmer.user
            user.first_name = mutable_data.get('first_name', user.first_name)
            user.last_name = mutable_data.get('last_name', user.last_name)
            user.gender = mutable_data.get('gender', user.gender)
            user.email = mutable_data.get('email', user.email)
            user.save()

            return Response(FullFarmerSerializer(farmer).data, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['GET'], url_path='me')
    def me(self, request):
        return Response(MobileUserWithTokenAndFarmerSerializer(request.user).data, status=status.HTTP_200_OK)
