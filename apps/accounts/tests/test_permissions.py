import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.tests.factory import AppPermissionFactory, UserFactory
from apps.shared.literals import (
    VIEW_GROUPS_AND_ROLES
)

User = get_user_model()


@pytest.mark.django_db
class TestPermissionListView:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.content_type = ContentType.objects.get_for_model(User)
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def test_list_permissions(self):
        # Assign view permission using the literal from shared.literals
        permission = Permission.objects.get(
            content_type=self.content_type,
            codename=VIEW_GROUPS_AND_ROLES
        )
        self.user.user_permissions.add(permission)

        # Create some test permissions
        custom_perm = AppPermissionFactory(
            codename='custom_action',
            content_type=self.content_type,
            name='Can perform custom action'
        )
        django_perm = AppPermissionFactory(
            codename='add_something',
            content_type=self.content_type,
            name='Can add something'
        )

        url = reverse('permissions')
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert any(perm['codename'] == custom_perm.codename for perm in response.data)
        assert not any(perm['codename'] == django_perm.codename for perm in response.data)

    def test_list_permissions_unauthorized(self):
        url = reverse('permissions')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN
