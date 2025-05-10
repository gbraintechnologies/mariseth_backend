from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.farm.views.farmer import FarmerViewSet
from apps.farm.views.farm import FarmViewSet
from apps.farm.views.products import ProductViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'farm', FarmViewSet, basename='farms')
router.register(r'farmer', FarmerViewSet, basename='farmers')
router.register(r'product', ProductViewSet, basename='product')

urlpatterns = [
    path('', include(router.urls)),
]
