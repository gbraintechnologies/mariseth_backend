from django.urls import path, include
from rest_framework.routers import DefaultRouter

from apps.accounts.views.auth import UserAuthViewSet
from apps.accounts.views.users import GroupsView, PermissionListView, UserAccountViewSet

router = DefaultRouter(trailing_slash=False)
router.register(r'accounts/users/admin', UserAccountViewSet, basename='users')
router.register(r'accounts/auth', UserAuthViewSet, basename='auth')

urlpatterns = [
    path('accounts/users/permissions', PermissionListView.as_view(), name='permissions'),
    path('accounts/users/groups', GroupsView.as_view(
        {'get': 'list', 'post': 'create'}
    ), name='groups'),
    path('accounts/users/groups/<int:pk>', GroupsView.as_view(
        {'put': 'update', 'delete': 'destroy'}
    ),
         name='groups'
         ),
    path('', include(router.urls)),
]
