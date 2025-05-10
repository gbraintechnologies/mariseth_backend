import json

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission, Group
from django.contrib.contenttypes.models import ContentType
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import GroupRank
from apps.accounts.tests.factory import AppGroupFactory, AppPermissionFactory, GroupRankFactory, UserFactory
from apps.shared.literals import ADD_ADMIN, DELETE_ADMIN, LIST_ADMINS, UPDATE_ADMIN

User = get_user_model()


# pytest -v apps/accounts/tests/test_users.py


@pytest.mark.django_db
class TestUserAccountViewSet:
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

    def test_create_user_without_permission(self):
        url = reverse('users-list')
        new_user = UserFactory.build()
        payload = {
            'email': new_user.email,
            'first_name': new_user.first_name,
            'last_name': new_user.last_name,
            'username': new_user.username,
            'phone_number': new_user.phone_number,
            'gender': new_user.gender,
            'avatar': None,
            'group': None,
        }
        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_create_user_with_permission(self):
        self._assign_permission(ADD_ADMIN)
        url = reverse('users-list')

        # Create group with permissions
        permission1 = AppPermissionFactory()
        permission2 = AppPermissionFactory()
        group = AppGroupFactory()
        group.permissions.add(permission1, permission2)

        # Use the group for the user payload
        new_user = UserFactory.build()
        payload = {
            'email': new_user.email,
            'first_name': new_user.first_name,
            'last_name': new_user.last_name,
            'username': new_user.username,
            'phone_number': '100000000011',  # Ensure phone_number is valid
            'gender': new_user.gender,
            'avatar': None,
            'group': group.id,  # Assign the created group to the user
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_201_CREATED
        assert response.data['email'] == payload['email']
        assert response.data['username'] == payload['username']

    def test_create_user_with_invalid_phone_number(self):
        self._assign_permission(ADD_ADMIN)
        url = reverse('users-list')
        group = AppGroupFactory()
        new_user = UserFactory.build()
        payload = {
            'email': new_user.email,
            'first_name': new_user.first_name,
            'last_name': new_user.last_name,
            'username': new_user.username,
            'phone_number': '12345',
            'gender': new_user.gender,
            'avatar': None,
            'group': group.id,
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert 'phone_number' in response.data

    def test_update_user_without_permission(self):
        user = UserFactory()
        url = reverse('users-detail', kwargs={'pk': user.id})
        payload = {
            'first_name': 'Updated Name',
            'phone_number': '100000002222'
        }
        response = self.client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_update_user_with_permission(self):
        self._assign_permission(UPDATE_ADMIN)
        user = UserFactory()
        url = reverse('users-detail', kwargs={'pk': user.id})
        payload = {
            'first_name': 'Updated Name',
            'phone_number': '100000002222'
        }

        response = self.client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['first_name'] == payload['first_name']
        assert response.data['phone_number'] == payload['phone_number']

    def test_partial_update_user_without_permission(self):
        user = UserFactory()
        url = reverse('users-detail', kwargs={'pk': user.id})
        payload = {
            'last_name': 'New Last Name'
        }
        response = self.client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_partial_update_user_with_permission(self):
        self._assign_permission(UPDATE_ADMIN)
        user = UserFactory()
        url = reverse('users-detail', kwargs={'pk': user.id})
        payload = {
            'last_name': 'New Last Name'
        }

        response = self.client.put(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_200_OK
        assert response.data['last_name'] == payload['last_name']

    def test_delete_user_without_permission(self):
        user = UserFactory()
        url = reverse('users-detail', kwargs={'pk': user.id})
        response = self.client.delete(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_delete_user_with_permission(self):
        self._assign_permission(DELETE_ADMIN)
        user = UserFactory()
        url = reverse('users-detail', kwargs={'pk': user.id})

        response = self.client.delete(url)

        assert response.status_code == status.HTTP_200_OK

    def test_delete_nonexistent_user_with_permission(self):
        self._assign_permission(DELETE_ADMIN)
        url = reverse('users-detail', kwargs={'pk': 9999})
        response = self.client.delete(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'User not found' in str(response.data['error'])

    def test_retrieve_user_without_permission(self):
        user = UserFactory()
        url = reverse('users-detail', kwargs={'pk': user.id})
        response = self.client.get(url)
        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_retrieve_user_with_permission(self):
        self._assign_permission(LIST_ADMINS)
        user = UserFactory()
        url = reverse('users-detail', kwargs={'pk': user.id})

        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert response.data['id'] == user.id

    def test_retrieve_nonexistent_user_with_permission(self):
        self._assign_permission(LIST_ADMINS)
        url = reverse('users-detail', kwargs={'pk': 9999})
        response = self.client.get(url)

        assert response.status_code == status.HTTP_404_NOT_FOUND
        assert 'User not found' in str(response.data['error'])

    def test_create_user_duplicate_username_with_permission(self):
        self._assign_permission(ADD_ADMIN)
        existing_user = UserFactory(username='unique_username')
        url = reverse('users-list')
        payload = {
            'email': 'duplicate@example.com',
            'first_name': 'Duplicate',
            'last_name': 'User',
            'username': existing_user.username,  # Duplicate username
            'phone_number': '1000000033',
            'gender': 'f',
            'avatar': None,
            'group': None,
        }

        response = self.client.post(
            url,
            data=json.dumps(payload),
            content_type='application/json'
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    def test_list_users_with_query_without_permission(self):
        user = UserFactory(username='searched_user')
        url = reverse('users-list') + '?query=searched_user'
        response = self.client.get(url)

        assert response.status_code == status.HTTP_403_FORBIDDEN

    def test_list_users_with_query_with_permission(self):
        self._assign_permission(LIST_ADMINS)
        user = UserFactory(username='searched_user')
        url = reverse('users-list') + '?query=searched_user'
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert any(u['username'] == 'searched_user' for u in response.data['results'])

    def test_list_users_pagination_with_permission(self):
        self._assign_permission(LIST_ADMINS)
        UserFactory.create_batch(15)  # Create multiple users to test pagination
        url = reverse('users-list') + '?page=1&page_size=10'
        response = self.client.get(url)

        assert response.status_code == status.HTTP_200_OK
        assert len(response.data['results']) <= 10
        assert 'pagination' in response.data
        assert response.data['pagination']['has_next'] is True
