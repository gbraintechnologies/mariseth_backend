from django.contrib import admin

from .models import Organization, OrganizationUser


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'address', 'date_created', 'date_modified', 'is_active')
    list_filter = ('is_active', 'date_created', 'date_modified')
    search_fields = ('name', 'address')
    ordering = ('name',)

    def get_inline_instances(self, request, obj=None):
        if not obj:
            return []
        return super().get_inline_instances(request, obj)


@admin.register(OrganizationUser)
class OrganizationUserAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'organization', 'date_created', 'date_modified', 'is_active')
    list_filter = ('is_active', 'organization', 'date_created', 'date_modified')
    search_fields = ('user__username', 'user__email', 'organization__name',)
    ordering = ('user',)
