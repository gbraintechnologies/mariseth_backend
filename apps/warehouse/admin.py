from django.contrib import admin

from .models import Warehouse, WarehouseProduct, WarehouseProductMovement


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
    inlines = [WarehouseProductInline]
    fieldsets = (
        (None, {
            'fields': ('organization', 'warehouse_id', 'name', 'region', 'district', 'capacity', 'manager', 'is_active')
        }),
        ('Audit Info', {
            'fields': ('date_created', 'date_modified', 'created_by', 'date_deleted', 'deleted_by'),
        }),
    )
    readonly_fields = ('date_created', 'date_modified', 'created_by', 'date_deleted', 'deleted_by')


class WarehouseProductMovementInline(admin.TabularInline):
    model = WarehouseProductMovement
    extra = 0
    fields = ('movement_type', 'quantity', 'weight', 'date', 'amount', 'buyer', 'aggregator', 'procurement_officer',
              'description', 'notes')
    readonly_fields = ('date',)


@admin.register(WarehouseProduct)
class WarehouseProductAdmin(admin.ModelAdmin):
    list_display = ('product', 'warehouse', 'quantity', 'weight', 'is_active')
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


@admin.register(WarehouseProductMovement)
class WarehouseProductMovementAdmin(admin.ModelAdmin):
    list_display = ('warehouse_product', 'movement_type', 'quantity', 'weight', 'date', 'amount', 'buyer', 'aggregator',
                    'procurement_officer', 'is_active')
    list_filter = (
        'movement_type', 'date', 'buyer', 'aggregator', 'procurement_officer', 'is_active',
        'warehouse_product__warehouse',
        'product', 'warehouse_product__organization')
    search_fields = ('warehouse_product__product__name', 'warehouse_product__warehouse__name', 'description', 'notes')
    fieldsets = (
        (None, {
            'fields': (
                'warehouse_product', 'product', 'movement_type', 'quantity', 'weight', 'amount', 'buyer', 'aggregator',
                'procurement_officer', 'description', 'notes', 'is_active')
        }),
        ('Audit Info', {
            'fields': ('date_created', 'date_modified', 'created_by', 'date_deleted', 'deleted_by'),
        }),
    )
    readonly_fields = ('date', 'date_created', 'date_modified', 'created_by', 'date_deleted', 'deleted_by')
