from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.customers.views import CustomerViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'customer', CustomerViewSet, basename='customer')

urlpatterns = [
    path('', include(router.urls)),
]
