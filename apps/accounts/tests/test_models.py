import re

import pytest
from django.contrib.auth.models import Permission
from django.contrib.contenttypes.models import ContentType
from django.utils import timezone

from apps.accounts.models import AppGroup, AppPermission, User
from apps.accounts.tests.factory import AppGroupFactory, UserFactory


@pytest.mark.django_db
def test_user_creation():
    user = UserFactory()
    assert user is not None
    assert re.match(
        r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$",
        user.email
    )
    assert user.first_name != ''
    assert user.gender in ['m', 'f']


@pytest.mark.django_db
def test_user_verification_code():
    user = UserFactory()
    verification_code = user.set_email_verification_code()
    assert user.verification_code == verification_code
    assert 100000 <= verification_code <= 999999


@pytest.mark.django_db
def test_user_verification_status():
    user = UserFactory()

    # Simulating the user verification step
    user.set_is_verified()
    assert user.is_verified
    assert user.date_verified is not None
    assert isinstance(user.date_verified, timezone.datetime)


@pytest.mark.django_db
def test_username_field():
    user = UserFactory()
    assert user.USERNAME_FIELD == 'email'


@pytest.mark.django_db
def test_required_fields():
    user = UserFactory()
    assert 'username' in user.REQUIRED_FIELDS


@pytest.mark.django_db
def test_permission_manager_get_permissions():
    content_type = ContentType.objects.get_for_model(User)
    regular_perm1 = Permission.objects.create(
        codename='add_something',
        name='Add Something',
        content_type=content_type
    )
    regular_perm2 = Permission.objects.create(
        codename='custom_action',
        name='Custom Action',
        content_type=content_type
    )

    filtered_perms = AppPermission.objects.get_permissions()
    assert regular_perm1 not in filtered_perms
    assert regular_perm2 in filtered_perms


@pytest.mark.django_db
def test_group_manager_get_groups():
    active_group = AppGroupFactory()
    active_group.ranking.is_active = True
    active_group.ranking.save()

    inactive_group = AppGroupFactory()
    inactive_group.ranking.is_active = False
    inactive_group.ranking.save()
    all_groups = AppGroup.objects.get_groups(is_active=False)
    assert active_group in all_groups
    assert inactive_group in all_groups
    active_groups = AppGroup.objects.get_groups(is_active=True)
    assert active_group in active_groups
    assert inactive_group not in active_groups


@pytest.mark.django_db
def test_group_manager_get_super_admin_group():
    # Create super admin group
    super_admin = AppGroupFactory(name='Super Admin')
    super_admin.ranking.is_default = True
    super_admin.ranking.save()

    # Create regular group
    regular_group = AppGroupFactory(name='Regular Group')

    retrieved_group = AppGroup.objects.get_super_admin_group()
    assert retrieved_group == super_admin
    assert retrieved_group != regular_group
