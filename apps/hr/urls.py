from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.hr.views.department import DepartmentViewSet
from apps.hr.views.job_title import JobTitleViewSet
from apps.hr.views.employee import EmployeeViewSet
from apps.hr.views.leave import LeaveRequestViewSet, LeaveTypeViewSet
from apps.hr.views.training import TrainingViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r"department", DepartmentViewSet, basename='department')
router.register(r"job-title", JobTitleViewSet, basename='job-title')
router.register(r'employee', EmployeeViewSet, basename='employee')
router.register(r'leave-type', LeaveTypeViewSet, basename='leave-type')
router.register(r'leave', LeaveRequestViewSet, basename='leave-request')
router.register(r'training', TrainingViewSet, basename='training')

urlpatterns = [
    path("", include(router.urls)),
]