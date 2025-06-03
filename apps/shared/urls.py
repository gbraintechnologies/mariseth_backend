from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.shared.views.app_settings import AppSettingViewSet
from apps.shared.views.custom_types import CustomTypeViewSet
from apps.shared.views.regions import RegionViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'custom-type', CustomTypeViewSet, basename='custom_types')
router.register(r'app-settings', AppSettingViewSet, basename='app_settings')
router.register(r'regions', RegionViewSet, basename='region')


urlpatterns = [
    path('', include(router.urls)),
]
