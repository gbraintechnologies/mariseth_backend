from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.shared.views.app_settings import AppSettingViewSet
from apps.shared.views.custom_types import CustomTypeViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'custom-type', CustomTypeViewSet, basename='custom_types')
router.register(r'app-settings', AppSettingViewSet, basename='app_settings')


urlpatterns = [
    path('', include(router.urls)),
]
