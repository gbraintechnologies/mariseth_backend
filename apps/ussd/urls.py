from django.urls import include, path
from rest_framework.routers import DefaultRouter
from apps.ussd.views.ussd import UssdViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'ussd', UssdViewSet, basename='ussd')

urlpatterns = [
    path('', include(router.urls)),
]
