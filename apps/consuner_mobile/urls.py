from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.consuner_mobile.views.auth import MobileUserAuthViewSet

# Create your tests here.

router = DefaultRouter(trailing_slash=False)
router.register(r'/auth', MobileUserAuthViewSet, basename='consumer')

urlpatterns = [
    path('', include(router.urls)),
]
