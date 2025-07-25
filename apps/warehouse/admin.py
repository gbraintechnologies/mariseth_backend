from django.contrib import admin
from django.contrib.auth import get_user_model

from .models import Warehouse, WarehouseProduct, WarehouseProductMovement

User = get_user_model()


class WarehouseProductMovementInline(admin.TabularInline):
    model = WarehouseProductMovement
    extra = 0
    fields = (
        'movement_type', 'quantity', 'weight', 'record_date',
        'amount', 'buyer', 'aggregator', 'procurement_officer',
        'description', 'notes')
    readonly_fields = (
        'movement_type', 'quantity', 'weight', 'record_date',
        'amount', 'buyer', 'aggregator', 'procurement_officer',
        'description', 'notes')


class WarehouseProductInline(admin.TabularInline):
    model = WarehouseProduct
    extra = 0
    fields = ('product', 'quantity', 'weight')
    readonly_fields = ('product',)


class UserWarehouseInline(admin.TabularInline):
    # This inline allows managing the many-to-many relationship between Warehouse and User (managers).
    # The 'through' argument is not needed here as Django automatically creates an intermediate table.
    model = Warehouse.managers.through
    extra = 1  # Number of empty forms to display
    verbose_name = "Manager"
    verbose_name_plural = "Managers"


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    # Removed 'manager' from list_display as it's now a ManyToManyField.
    # ManyToManyFields cannot be directly displayed in list_display.
    list_display = ('id', 'name', 'warehouse_id', 'region', 'district', 'capacity', 'is_active')
    list_filter = ('region', 'district', 'is_active', 'organization')
    # Removed 'manager__username' from search_fields as ManyToManyFields are not directly searchable this way.
    search_fields = ('name', 'warehouse_id', 'region__name', 'district__name')
    # Added UserWarehouseInline to manage managers directly in the Warehouse admin page.
    inlines = [WarehouseProductInline, WarehouseProductMovementInline, UserWarehouseInline]
    fieldsets = (
        (None, {
            # Removed 'manager' from fields as it's now handled by the inline.
            'fields': ('organization', 'warehouse_id', 'name', 'region', 'district', 'capacity', 'is_active')
        }),
        ('Audit Info', {
            'fields': ('date_created', 'date_modified', 'created_by', 'date_deleted', 'deleted_by'),
        }),
    )
    readonly_fields = ('date_created', 'date_modified', 'created_by', 'date_deleted', 'deleted_by')


@admin.register(WarehouseProduct)
class WarehouseProductAdmin(admin.ModelAdmin):
    list_display = ('id', 'product__id', 'warehouse__id', 'product', 'warehouse', 'quantity', 'weight', 'is_active')
    list_filter = ('warehouse', 'product', 'is_active', 'organization')
    search_fields = ('product__name', 'warehouse__name', 'warehouse__warehouse_id')
    inlines = [WarehouseProductMovementInline]
    fieldsets = (
        (None, {
            'fields': ('organization', 'product', 'warehouse', 'quantity', 'weight', 'is_active')
        }),
        ('Audit Info', {
            'fields': ('date_created', 'date_modified', 'created_by', 'date_deleted', 'deleted_by'),
        }),
    )
    readonly_fields = ('date_created', 'date_modified', 'created_by', 'date_deleted', 'deleted_by')
