from django.contrib import admin

from .models import Warehouse, WarehouseProduct, WarehouseProductMovement


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


@admin.register(Warehouse)
class WarehouseAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'warehouse_id', 'region', 'district', 'capacity', 'manager', 'is_active')
    list_filter = ('region', 'district', 'is_active', 'organization')
    search_fields = ('name', 'warehouse_id', 'region', 'district', 'manager__username')
    inlines = [WarehouseProductInline, WarehouseProductMovementInline]
    fieldsets = (
        (None, {
            'fields': ('organization', 'warehouse_id', 'name', 'region', 'district', 'capacity', 'manager', 'is_active')
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
