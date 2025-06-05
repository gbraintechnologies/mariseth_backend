

import random

from django.contrib.auth.models import AbstractUser, Permission, PermissionsMixin, UserManager
from django.core.exceptions import ValidationError
from django.core.validators import MinLengthValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.shared.literals import (
    ADD_ADMIN, APPROVE_INFLOW_DELIVERY_INSPECTION, APPROVE_INFLOW_ORDER, APPROVE_OR_DENY_CREDIT, CREATE_CREDIT,
    CREATE_CUSTOMER, CREATE_CUSTOM_TYPE, CREATE_FARM, CREATE_FARMER, CREATE_GROUPS_AND_ROLES, CREATE_INFLOW_ORDER,
    CREATE_OR_UPDATE_SETTINGS, CREATE_PAYBACK, CREATE_PRODUCT, CREATE_WAREHOUSE, DELETE_ADMIN, DELETE_CREDIT,
    DELETE_CUSTOMER, DELETE_CUSTOM_TYPE, DELETE_FARM, DELETE_FARMER, DELETE_FARM_PRODUCTS, DELETE_GROUPS_AND_ROLES,
    DELETE_INFLOW_ORDER, DELETE_PRODUCT, DELETE_WAREHOUSE, GET_SMALLHOLDERS_BY_LEAD, LIST_ADMINS, LIST_CREDITS,
    LIST_CUSTOMERS, LIST_FARMERS, LIST_FARMS, LIST_INFLOW_ORDERS, LIST_PAYBACKS, LIST_PRODUCTS, LIST_WAREHOUSES,
    UPDATE_ADMIN, UPDATE_CREDIT, UPDATE_CUSTOMER, UPDATE_CUSTOM_TYPE, UPDATE_FARM, UPDATE_FARMER,
    UPDATE_GROUPS_AND_ROLES, UPDATE_INFLOW_ORDER, UPDATE_PAYBACK, UPDATE_PRODUCT, UPDATE_WAREHOUSE, UPLOAD_WAREHOUSES,
    VIEW_CREDIT, VIEW_FARM, VIEW_FARMER, VIEW_GROUPS_AND_ROLES, VIEW_INFLOW_ORDER, VIEW_PRODUCT, VIEW_WAREHOUSE
)
from apps.shared.models import BaseModel
from apps.shared.overrides import FileNameEngine
from apps.shared.utils.validators import validate_only_digits


class PermissionManager(models.Manager):
    def get_permissions(self, *args, **kwargs):
        """
        Custom manager method to get filtered permissions.
        """
        return super().get_queryset().exclude(
            Q(codename__startswith='add_') |
            Q(codename__startswith='change_') |
            Q(codename__startswith='delete_') |
            Q(codename__startswith='view_')
        )


class AppPermission(Permission):
    """
    Proxy model to attach the custom manager to the built-in Permission model.
    """
    objects = PermissionManager()

    class Meta:
        proxy = True


class GroupManager(models.Manager):
    def get_groups(self, is_active=False, *args, **kwargs):
        if is_active:
            return AppGroup.objects.filter(is_active=True)
        return AppGroup.objects.all()

    def get_super_admin_group(self, *args, **kwargs):
        return AppGroup.objects.get(is_active=True, name='Super Admin', is_default=True)


class AppGroup(BaseModel):
    name = models.CharField(max_length=150)
    organization = models.ForeignKey(
        'organizations.Organization',
        on_delete=models.CASCADE,
        related_name='custom_groups',
        null=True, blank=True
    )
    description = models.TextField(null=True, blank=True)
    is_default = models.BooleanField(default=False)
    rank = models.PositiveIntegerField(null=True, blank=True)
    permissions = models.ManyToManyField(
        Permission,
        blank=True,
        related_name='app_groups',
        help_text='The permissions assigned to this group.'
    )

    class Meta:
        ordering = ['rank', 'name']
        unique_together = ['name', 'organization']
        verbose_name = 'Group'
        verbose_name_plural = 'Groups'

    objects = GroupManager()

    def clean(self):
        existing_groups = AppGroup.objects.filter(is_active=True).exclude(id=self.id if self.id else None)

        # Validate uniqueness for default groups
        if self.is_default:
            if existing_groups.filter(name=self.name, is_default=True).exists():
                raise ValidationError({'name': 'A default group with this name already exists.'})

        # Validate uniqueness across organization groups
        if self.organization:
            if existing_groups.filter(name=self.name, organization=self.organization).exists():
                raise ValidationError({'name': 'A group with this name already exists in this organization.'})

        # Validate global uniqueness of names for default and non-default groups
        if existing_groups.filter(name=self.name, is_default=True).exists():
            raise ValidationError(
                {'name': 'A group with this name already exists as a default group and cannot be duplicated.'})

        super().clean()

    def __str__(self):
        if self.is_default:
            return f'{self.id} - {self.name} (Default)'
        return f'{self.id} - {self.name} - {self.organization.name if self.organization else "Global"}'


class CustomUserManager(UserManager):
    """
    Custom manager for User model to add additional methods.
    """

    def get_users_with_permission(self, permission):
        """
        Retrieve all users who have a given permission or are superusers.

        Args:
            permission (str): The codename of the permission to check.

        Returns:
            QuerySet: A queryset of User instances that have the specified permission or are superusers.
        """
        # Get the permission object
        try:
            permission = Permission.objects.get(codename=permission)
        except Permission.DoesNotExist:
            # Handle the case where the permission does not exist
            return self.none()

        # Query for users with the permission directly, through a group, or who are superusers
        return self.get_queryset().filter(
            Q(user_permissions=permission) |
            Q(groups__permissions=permission) | Q(is_superuser=True)
        ).distinct()


class User(AbstractUser, BaseModel, PermissionsMixin):
    GENDER_CHOICES = (
        ('m', 'Male'),
        ('f', 'Female')
    )
    USER_TYPE_CHOICES = (
        ('admin', 'Admin'),
        ('user', 'User')
    )
    STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive')
    )
    gender = models.CharField(choices=GENDER_CHOICES,
                              max_length=10, blank=True, null=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    email = models.EmailField(unique=True)
    phone_number = models.CharField(unique=True, max_length=40, blank=False, null=True,
                                    validators=[
                                        MinLengthValidator(
                                            11, "Phone number number must be at least 11 characters."),
                                        validate_only_digits], )
    avatar = models.ImageField(upload_to=FileNameEngine(
        'avatars/'), null=True, blank=True)
    verification_code = models.IntegerField(blank=True, null=True)
    is_verified = models.BooleanField(default=False)
    date_verified = models.DateTimeField(blank=True, null=True)
    user_type = models.CharField(choices=USER_TYPE_CHOICES, max_length=10)
    status = models.CharField(choices=STATUS_CHOICES, max_length=10, default='active')

    groups = models.ManyToManyField(
        AppGroup,
        verbose_name=("groups"),
        blank=True,
        help_text=(
            "The groups this user belongs to. A user will get all permissions "
            "granted to each of their groups."
        ),
        related_name="user_set",
        related_query_name="user",
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'phone_number']
    objects = CustomUserManager()

    class Meta:
        permissions = [
            (VIEW_GROUPS_AND_ROLES, 'view groups and roles'),
            (CREATE_GROUPS_AND_ROLES, 'create new groups and assign roles'),
            (UPDATE_GROUPS_AND_ROLES, 'update existing groups and their roles'),
            (DELETE_GROUPS_AND_ROLES, 'delete groups and their roles'),

            (ADD_ADMIN, 'add admin'),
            (LIST_ADMINS, 'list admins'),
            (DELETE_ADMIN, 'delete admin'),
            (UPDATE_ADMIN, 'update admin'),

            (CREATE_CUSTOM_TYPE, 'create custom type'),
            (UPDATE_CUSTOM_TYPE, 'update custom type'),
            (DELETE_CUSTOM_TYPE, 'delete custom type'),
            (CREATE_OR_UPDATE_SETTINGS, 'create or update settings'),

            # fmrms
            (CREATE_FARM, 'create a farm'),
            (UPDATE_FARM, 'update a farm'),
            (DELETE_FARM, 'delete a farm'),
            (VIEW_FARM, 'view a farm'),
            (LIST_FARMS, 'list all farms'),
            (DELETE_FARM_PRODUCTS, 'remove a product from a farm'),
            # farms
            # (UPLOAD_FARMS, ''),
            (CREATE_FARMER, 'create a farmer'),
            (UPDATE_FARMER, 'update a farmer'),
            (DELETE_FARMER, 'delete a farmer'),
            (LIST_FARMERS, 'list all farmers'),
            (VIEW_FARMER, 'view a farmer'),
            (GET_SMALLHOLDERS_BY_LEAD, 'get smallholders by lead'),

            # (UPLOAD_FARMERS, ''),
            # products
            (CREATE_PRODUCT, 'create a product'),
            (UPDATE_PRODUCT, 'update a product'),
            (DELETE_PRODUCT, 'delete a product'),
            (LIST_PRODUCTS, 'list all products'),
            (VIEW_PRODUCT, 'view a product'),
            # (UPLOAD_PRODUCTS, ''),
            # credit
            (CREATE_CREDIT, 'create a credit'),
            (UPDATE_CREDIT, 'update a credit'),
            (DELETE_CREDIT, 'delete a credit'),
            (VIEW_CREDIT, 'view a credit'),
            (LIST_CREDITS, 'list all credits'),
            # (UPLOAD_CREDITS, ''),
            (APPROVE_OR_DENY_CREDIT, 'approve or deny credit'),
            # paybacks
            (CREATE_PAYBACK, 'create a payback for a credit'),
            (UPDATE_PAYBACK, 'update a payback for a credit'),
            (LIST_PAYBACKS, 'list all paybacks'),

            # warehouse
            (CREATE_WAREHOUSE, 'create a warehouse'),
            (UPDATE_WAREHOUSE, 'update a warehouse'),
            (DELETE_WAREHOUSE, 'delete a warehouse'),
            (VIEW_WAREHOUSE, 'view a warehouse'),
            (LIST_WAREHOUSES, 'list all warehouses'),
            (UPLOAD_WAREHOUSES, 'upload warehouses'),

            # inflow
            (CREATE_INFLOW_ORDER, 'create an inflow order'),
            (UPDATE_INFLOW_ORDER, 'update an inflow order'),
            (DELETE_INFLOW_ORDER, 'delete an inflow order'),
            (VIEW_INFLOW_ORDER, 'view an inflow order'),
            (LIST_INFLOW_ORDERS, 'list all inflows orders'),
            (APPROVE_INFLOW_DELIVERY_INSPECTION, 'approve inflow delivery inspection'),
            (APPROVE_INFLOW_ORDER, 'approve an inflow order'),

            # customers
            (CREATE_CUSTOMER, 'create a customer'),
            (UPDATE_CUSTOMER, 'update a customer'),
            (DELETE_CUSTOMER, 'delete a customer'),
            (LIST_CUSTOMERS, 'list all customers'),
        ]

    def set_email_verification_code(self):
        self.verification_code = random.randint(100000, 999999)
        self.save()
        return self.verification_code

    def set_is_verified(self):
        self.is_verified = True
        self.verified_on = timezone.now()
        self.save()

    @property
    def is_super_admin(self):
        return self.groups.filter(name='Super Admin', is_default=True, is_active=True).exists()

    def has_perm(self, perm, obj=None):
        """
        Minimal override to check:
         1. is_active -> must be True
         2. is_superuser -> automatically True
         3. user_permissions -> direct perms
         4. groups (AppGroup) -> group perms
        """
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        codename = self._get_custom_perm_identifier(perm)
        if self.user_permissions.filter(codename=codename).exists():
            return True
        return self.groups.filter(permissions__codename=codename).exists()

    def _get_custom_perm_identifier(self, perm):
        """
        Optional helper: if 'perm' might be 'app_label.codename' or 'app_label|codename',
        parse out just the codename. Adapt to your format if needed.
        """
        if '.' in perm:
            return perm.split('.')[-1]
        if '|' in perm:
            return perm.split('|')[-1]
        return perm

    def has_module_perms(self, app_label):
        """
        If you want to check module-level perms. For minimal changes,
        just rely on the default or do a custom approach.
        """
        if not self.is_active:
            return False
        if self.is_superuser:
            return True
        if self.user_permissions.filter(content_type__app_label=app_label).exists():
            return True
        return self.groups.filter(permissions__content_type__app_label=app_label).exists()

    def __str__(self):
        return f'{self.id}-{self.get_full_name()}'


class UserChangeLog(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='change_logs')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, null=True, blank=True,
                                     related_name='user_change_logs')
    action = models.CharField(max_length=50)
    field_name = models.CharField(max_length=255, null=True, blank=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'ChangeLog({self.user.email}, {self.action}, {self.field_name})'
