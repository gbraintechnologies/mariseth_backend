from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.organizations.views.organization import OrganizationViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'organization', OrganizationViewSet, basename='organization')


urlpatterns = [
    path('', include(router.urls)),
]
