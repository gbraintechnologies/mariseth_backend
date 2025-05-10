from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from apps.shared.literals import CREATE_OR_UPDATE_SETTINGS
from apps.shared.models import AppSetting
from apps.shared.serializers.app_settings import AppSettingSerializer
from apps.shared.swagger import add_swagger_to_app_setting_viewset
from apps.shared.utils.permissions import UserPermission


@add_swagger_to_app_setting_viewset
class AppSettingViewSet(ViewSet):
    def get_permissions(self):
        permissions = {
            'create_or_update_settings': CREATE_OR_UPDATE_SETTINGS,
        }
        user_permission = permissions.get(self.action, None)
        if user_permission:
            return [IsAuthenticated(), UserPermission(user_permission)]
        return [IsAuthenticated()]

    @action(detail=False, methods=['get'])
    def get_settings(self, request):
        try:
            app_setting = AppSetting.objects.get(
                organization=request.organization,
                is_active=True
            )
            return Response(
                AppSettingSerializer(app_setting).data,
                status=status.HTTP_200_OK
            )
        except AppSetting.DoesNotExist:
            serializer = AppSettingSerializer(
                data={'organization': request.organization},
                context={'request': request}
            )
            if serializer.is_valid():
                app_setting = serializer.save()
                return Response(
                    AppSettingSerializer(app_setting).data,
                    status=status.HTTP_200_OK
                )
            return Response(
                {'error': 'Could not create default settings'},
                status=status.HTTP_400_BAD_REQUEST
            )

    @action(detail=False, methods=['post'], url_path='create-or-update-settings')
    def create_or_update_settings(self, request):
        try:
            app_setting = AppSetting.objects.get(
                organization=request.organization,
                is_active=True
            )
            serializer = AppSettingSerializer(
                instance=app_setting,
                data=request.data,
                partial=True,
                context={'request': request}
            )
            if serializer.is_valid():
                app_setting = serializer.save()
                return Response(
                    AppSettingSerializer(app_setting).data,
                    status=status.HTTP_200_OK
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except AppSetting.DoesNotExist:
            serializer = AppSettingSerializer(
                data=request.data,
                context={'request': request}
            )
            if serializer.is_valid():
                app_setting = serializer.save()
                return Response(
                    AppSettingSerializer(app_setting).data,
                    status=status.HTTP_201_CREATED
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
