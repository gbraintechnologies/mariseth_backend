from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.shared.views.app_settings import AppSettingViewSet
from apps.shared.views.custom_types import CustomTypeViewSet
from apps.shared.views.dashboard import DashboardViewSet
from apps.shared.views.regions import RegionViewSet
from apps.shared.views.audit_trail import AuditTrailViewSet
from apps.shared.views.help import HelpViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'custom-type', CustomTypeViewSet, basename='custom_types')
router.register(r'app-settings', AppSettingViewSet, basename='app_settings')
router.register(r'regions', RegionViewSet, basename='region')
router.register(r'dashboard', DashboardViewSet, basename='dashboard')
router.register(r'audit-trail', AuditTrailViewSet, basename='audit-trail')
router.register(r'help', HelpViewSet, basename='help')


urlpatterns = [
    path('', include(router.urls)),
]
