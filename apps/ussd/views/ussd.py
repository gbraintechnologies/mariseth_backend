from datetime import timedelta, datetime

from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import AllowAny
from rest_framework.decorators import permission_classes,action
from rest_framework.response import Response

from apps.ussd.models import UssdSession
from apps.ussd.serializers.ussd import UssdRequestSerializer, UssdSessionSerializer
from apps.ussd.services import UssdSessionService, UssdResult


class UssdViewSet(viewsets.GenericViewSet):
    serializer_class = UssdSessionSerializer
    queryset = UssdSession.objects.filter(is_active=True)
    authentication_classes = []
    ussd_session_service = UssdSessionService()
    permission_classes = [AllowAny]

    # @transaction.atomic
    # def get(self, request):
    #     serializer = UssdRequestSerializer(data=request.data)
    #     serializer.is_valid(raise_exception=True)
    #     phone_number = serializer.validated_data['phone_number']
    #     session_id = serializer.validated_data['session_id']
    #     user_id = serializer.validated_data.get('user_id', 'USSD_DOCUMENTATION')
    #     new_session = serializer.validated_data.get('new_session', False)
    #     user_data = serializer.validated_data.get('user_data', '')
    #     network = serializer.validated_data.get('network', '')
    #
    #     return self.ussd_session_service.handle_ussd_session(session_id
    #                       , user_id
    #                       , new_session
    #                       , phone_number
    #                       , user_data)
    @transaction.atomic
    def create(self, request):
        serializer = UssdRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        phone_number = serializer.validated_data['phone_number']
        session_id = serializer.validated_data['session_id']
        user_id = serializer.validated_data.get('user_id', 'USSD_DOCUMENTATION')
        new_session = serializer.validated_data.get('new_session', False)
        user_data = serializer.validated_data.get('user_data', '')
        network = serializer.validated_data.get('network', '')
        result = UssdResult("",True)
        try:
            result = self.ussd_session_service.ussd_callback(session_id
                              , user_id
                              , new_session
                              , phone_number
                              , user_data)
        except Exception as e:
            print(e)
        return Response(
            {
                'sessionID': session_id,
                'userID': user_id,
                'msisdn': phone_number,
                'message': result.message,
                'continueSession': result.continue_session,
            },
            status=status.HTTP_200_OK
        )
