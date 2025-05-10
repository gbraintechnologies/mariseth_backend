import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import GroupRank
from apps.accounts.tests.factory import AppGroupFactory, AppPermissionFactory, GroupRankFactory, UserFactory
from apps.shared.literals import (
    CREATE_GROUPS_AND_ROLES, DELETE_GROUPS_AND_ROLES,
    UPDATE_GROUPS_AND_ROLES, VIEW_GROUPS_AND_ROLES
)

User = get_user_model()


@pytest.mark.django_db
class TestGroupsViewSet:
    def setup_method(self):
        self.client = APIClient()
        self.user = UserFactory()
        self.group = Group(name='Super Admin')
        self.group.save()
        if not GroupRank.objects.filter(group=self.group).exists():
            GroupRankFactory(group=self.group, is_default=True)
        self.content_type = ContentType.objects.get_for_model(User)
        refresh = RefreshToken.for_user(self.user)
        self.access_token = str(refresh.access_token)
        self.client.credentials(HTTP_AUTHORIZATION=f'Bearer {self.access_token}')

    def _assign_permission(self, codename):
        """Helper method to assign permission to user"""
        permission = Permission.objects.get(
            content_type=self.content_type,
            codename=codename
        )
        self.user.user_permissions.add(permission)
        self.user = User.objects.get(pk=self.user.pk)

    def test_list_groups_unauthorized(self):
        url = reverse('groups')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_groups(self):
        # Create test groups
        active_group = AppGroupFactory()
        active_group.ranking.is_active = True
        active_group.ranking.save()

        inactive_group = AppGroupFactory()
        inactive_group.ranking.is_active = False
        inactive_group.ranking.save()

        # Assign view permission using the literal from shared.literals
        self._assign_permission(VIEW_GROUPS_AND_ROLES)

        url = reverse('groups')
        response = self.client.get(url)
        assert response.status_code == status.HTTP_200_OK
        assert len(response.data) >= 1
        assert any(group['id'] == active_group.id for group in response.data)
        assert not any(group['id'] == inactive_group.id for group in response.data)

    def test_create_group(self):
        # Assign create permission using the literal from shared.literals
        self._assign_permission(CREATE_GROUPS_AND_ROLES)
        url = reverse('groups')
        payload = {
            'name': 'Test Group',
            'rank': 1,
            'permissions': []
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['name'] == payload['name']
        assert response.data['rank'] == payload['rank']

    def test_update_group(self):
        self._assign_permission(UPDATE_GROUPS_AND_ROLES)

        # Create a non-default group
        group = AppGroupFactory()
        group.ranking.is_default = False
        group.ranking.save()

        url = reverse('groups', kwargs={'pk': group.id})
        payload = {
            'name': 'Updated Group Name',
            'rank': 90
        }
        response = self.client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == payload['name']
        assert response.data['rank'] == payload['rank']

    def test_delete_group(self):
        self._assign_permission(DELETE_GROUPS_AND_ROLES)

        # Create a non-default group with no users
        group = AppGroupFactory()
        group.ranking.is_default = False
        group.ranking.is_active = True
        group.ranking.save()

        url = reverse('groups', kwargs={'pk': group.id})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_200_OK

    def test_delete_group_with_users(self):
        self._assign_permission(DELETE_GROUPS_AND_ROLES)

        # Create a group and assign a user to it
        group = AppGroupFactory()
        group.ranking.is_active = True
        group.ranking.save()
        group.user_set.add(self.user)

        url = reverse('groups', kwargs={'pk': group.id})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Cannot delete a role with assigned users' in str(response.data['error'])

    def test_delete_default_group(self):
        self._assign_permission(DELETE_GROUPS_AND_ROLES)

        # Create a default group
        group = AppGroupFactory()
        group.ranking.is_default = True
        group.ranking.is_active = True
        group.ranking.save()

        url = reverse('groups', kwargs={'pk': group.id})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'Default role cannot be deleted' in str(response.data['error'])

    def test_create_group_duplicate_name(self):
        self._assign_permission(CREATE_GROUPS_AND_ROLES)

        url = reverse('groups')
        payload = {
            'name': self.group.name,  # Duplicate name
            'rank': 1,
            'permissions': []
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_partial_update_group_name(self):
        self._assign_permission(UPDATE_GROUPS_AND_ROLES)

        group = AppGroupFactory()
        group.ranking.is_default = False
        group.ranking.save()

        url = reverse('groups', kwargs={'pk': group.id})
        payload = {
            'name': 'Updated Group Name'
        }

        response = self.client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == payload['name']

    def test_partial_update_group_name(self):
        self._assign_permission(UPDATE_GROUPS_AND_ROLES)

        group = AppGroupFactory()
        group.ranking.is_default = False
        group.ranking.save()

        url = reverse('groups', kwargs={'pk': group.id})
        payload = {
            'name': 'Updated Group Name'
        }

        response = self.client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == payload['name']

    def test_partial_update_group_permissions(self):
        self._assign_permission(UPDATE_GROUPS_AND_ROLES)

        group = AppGroupFactory()
        group.ranking.is_default = False
        group.ranking.save()

        permission = AppPermissionFactory()
        url = reverse('groups', kwargs={'pk': group.id})
        payload = {
            'permissions': [permission.id]
        }

        response = self.client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert permission.id in [p['id'] for p in response.data['permissions']]

    def test_partial_update_group_remove_permissions(self):
        self._assign_permission(UPDATE_GROUPS_AND_ROLES)

        group = AppGroupFactory()
        group.ranking.is_default = False
        group.ranking.save()

        permission = AppPermissionFactory()
        group.permissions.add(permission)

        url = reverse('groups', kwargs={'pk': group.id})
        payload = {
            'permissions': []
        }

        response = self.client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['permissions'] == []

    def test_partial_update_group_multiple_fields(self):
        self._assign_permission(UPDATE_GROUPS_AND_ROLES)

        group = AppGroupFactory()
        group.ranking.is_default = False
        group.ranking.save()

        permission = AppPermissionFactory()
        url = reverse('groups', kwargs={'pk': group.id})
        payload = {
            'name': 'Updated Group Name',
            'rank': 80,
            'permissions': [permission.id]
        }

        response = self.client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['name'] == payload['name']
        assert response.data['rank'] == payload['rank']
        assert permission.id in [p['id'] for p in response.data['permissions']]
