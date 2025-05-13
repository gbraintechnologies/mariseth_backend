from django.contrib import admin

from apps.customers.models import Customer


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'customer_id', 'name', 'phone_number', 'email',
        'local', 'company', 'date_created', 'is_active'
    )
    list_filter = ('is_active', 'company', 'local', 'date_created')
    search_fields = ('name', 'phone_number', 'email', 'customer_id')
    readonly_fields = ('customer_id', 'date_created',)
    ordering = ('name',)
