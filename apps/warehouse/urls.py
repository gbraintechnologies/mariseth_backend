from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.warehouse.views import WarehouseViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'warehouse', WarehouseViewSet, basename='warehouse')

urlpatterns = [
    path('', include(router.urls)),
]
