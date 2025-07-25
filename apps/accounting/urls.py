from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.accounting.views.expenses import ExpenseViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'expenses', ExpenseViewSet, basename='expenses')


urlpatterns = [
    path('', include(router.urls)),
]
