from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group as DefaultGroup
from django.core.exceptions import ValidationError

from apps.accounts.models import AppGroup
from apps.organizations.models import OrganizationUser
from mariseth.settings.base import ENVIRONMENT

User = get_user_model()


class UserGroupInline(admin.TabularInline):
    model = User.groups.through
    extra = 1
    verbose_name = 'Group'
    verbose_name_plural = 'Groups'


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'first_name', 'last_name', 'email', 'get_groups', 'get_organization',
        'date_created', 'is_active', 'is_verified',
    )
    list_display_links = ('id', 'first_name', 'last_name', 'email')
    search_fields = ('first_name', 'last_name', 'email')
    list_filter = ('gender', 'is_verified')
    readonly_fields = ('id', 'date_verified')
    fieldsets = (
        ('Personal Info', {'fields': ('first_name', 'last_name', 'gender')}),
        ('Contact Info', {'fields': ('email', 'phone_number', 'username')}),
        ('Other Info', {'fields': ('avatar', 'verification_code', 'is_verified', 'date_verified')})
    )
    inlines = [UserGroupInline]

    def get_groups(self, obj):
        return ", ".join([group.name for group in obj.groups.all()])

    get_groups.short_description = 'Groups'

    def get_organization(self, obj):
        organization_user = OrganizationUser.objects.filter(user=obj).first()
        return organization_user.organization if organization_user else None

    get_organization.short_description = 'Organization'


@admin.register(AppGroup)
class AppGroupAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'organization', 'is_default', 'rank', 'get_is_active']
    list_display_links = ['id', 'name']
    list_filter = ['organization', 'is_default', 'is_active']
    ordering = ['rank', 'name']
    filter_horizontal = ['permissions']

    def get_is_active(self, obj):
        return obj.is_active

    get_is_active.short_description = 'Is Active'
    get_is_active.boolean = True

    def save_model(self, request, obj, form, change):
        try:
            obj.clean()
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            form.add_error(None, e.message_dict)
            raise


admin.site.unregister(DefaultGroup)
env_mapping = {
    'local': 'Local',
    'staging': 'Staging',
    'production': 'Production'
}

env_alias = env_mapping.get(ENVIRONMENT)
admin.site.site_header = f"Mariseth Backend - {env_alias}"
admin.site.site_title = f"Mariseth Backend - {env_alias}"
admin.site.index_title = f"Mariseth Backend Admin - {env_alias}"
