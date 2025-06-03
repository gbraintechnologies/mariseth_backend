from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.outflow.views.approvals import OutflowApprovalViewSet
from apps.outflow.views.outflow import OutflowOrderViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'outflow', OutflowOrderViewSet, basename='outflow')
router.register(r'outflow/approval', OutflowApprovalViewSet, basename='outflow-approval')

urlpatterns = [
    path('', include(router.urls)),
]
