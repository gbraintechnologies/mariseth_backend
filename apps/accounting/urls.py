from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounting.views.expenses import ExpenseViewSet
from apps.accounting.views.waybills import WaybillViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'expenses', ExpenseViewSet, basename='expenses')
router.register(r'waybill', WaybillViewSet, basename='waybill')


urlpatterns = [
    path('', include(router.urls)),
]
