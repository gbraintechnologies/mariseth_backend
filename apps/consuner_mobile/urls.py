from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.consuner_mobile.views.auth import MobileUserAuthViewSet
from apps.consuner_mobile.views.credit import MobileCreditViewSet

# Create your tests here.

router = DefaultRouter(trailing_slash=False)
router.register(r'/auth', MobileUserAuthViewSet, basename='auth')
router.register(r'/credit', MobileCreditViewSet, basename='credit')

urlpatterns = [
    path('', include(router.urls)),
]
