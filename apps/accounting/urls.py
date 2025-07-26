from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounting.views.expenses import ExpenseViewSet
from apps.accounting.views.waybills import WaybillViewSet
from apps.accounting.views.invoices import InvoiceViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'expenses', ExpenseViewSet, basename='expenses')
router.register(r'waybill', WaybillViewSet, basename='waybill')
router.register(r'invoice', InvoiceViewSet, basename='invoices')


urlpatterns = [
    path('', include(router.urls)),
]
