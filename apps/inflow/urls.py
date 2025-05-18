from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inflow.views import InflowOrderViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'inflow', InflowOrderViewSet, basename='inflow')

urlpatterns = [
    path('', include(router.urls)),
]
