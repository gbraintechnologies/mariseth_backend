from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.credit.views.credits import CreditViewSet
from apps.credit.views.payback import PaybackViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'credit', CreditViewSet, basename='credit')
router.register(r'payback', PaybackViewSet, basename='payback')

urlpatterns = [
    path('', include(router.urls)),
]
