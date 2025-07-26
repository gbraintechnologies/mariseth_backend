from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.hr.views import DepartmentViewSet, JobTitleViewSet
from apps.hr.views.employee import EmployeeViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r"department", DepartmentViewSet, basename='department')
router.register(r"job-title", JobTitleViewSet, basename='job-title')
router.register(r'employee', EmployeeViewSet, basename='employee')


urlpatterns = [
    path("", include(router.urls)),
]
