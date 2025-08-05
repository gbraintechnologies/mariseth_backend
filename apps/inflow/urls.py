from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.inflow.views import InflowOrderViewSet
from apps.inflow.approval_view import InflowOrderApprovalViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'inflow', InflowOrderViewSet, basename='inflow')
router.register(r'inflow-approvals', InflowOrderApprovalViewSet, basename='inflow-approval')

urlpatterns = [
    path('', include(router.urls)),
]
