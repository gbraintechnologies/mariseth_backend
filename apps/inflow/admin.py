# admin.py
from django.contrib import admin

from .models import InflowMedia, InflowOrder, InflowOrderHistory, InflowOrderProduct


class InflowOrderProductInline(admin.TabularInline):
    model = InflowOrderProduct
    extra = 0
    fields = ('id', 'serial_number', 'product', 'farm', 'quantity', 'unit_price', 'total_cost')
    readonly_fields = ('id', 'serial_number', 'total_cost')


class InflowMediaInline(admin.TabularInline):
    model = InflowMedia
    extra = 0
    fields = ('id', 'name', 'file', 'is_complaint', 'related_product')
    readonly_fields = ('id', 'name', 'file', 'is_complaint', 'related_product')


class InflowOrderHistoryInline(admin.TabularInline):
    model = InflowOrderHistory
    extra = 0
    fields = (
        'id', 'event_type', 'notes', 'old_value', 'new_value', 'field_name',
        'date_created', 'created_by'
    )
    readonly_fields = (
        'id', 'event_type', 'notes', 'old_value',
        'new_value', 'field_name', 'date_created', 'created_by'
    )


@admin.register(InflowOrder)
class InflowOrderAdmin(admin.ModelAdmin):
    inlines = (InflowOrderProductInline, InflowMediaInline, InflowOrderHistoryInline)
    list_display = (
        "id", 'order_id', 'waybill_id', 'aggregator', 'procurement_officer',
        'destination_warehouse', 'status', 'is_active'
    )
    list_filter = ('status', 'aggregator', 'procurement_officer')
    search_fields = ('order_id', 'aggregator__username', 'procurement_officer__username')
    readonly_fields = ('total_cost', 'total_products_cost', 'total_bags', 'waybill_id')

#
# @admin.register(InflowOrderProduct)
# class InflowOrderProductAdmin(admin.ModelAdmin):
#     list_display = ('serial_number', 'order', 'product', 'farm', 'quantity', 'unit_price', 'total_cost')
#     search_fields = ('serial_number', 'order__order_id', 'product__name', 'farm__name')
#
#
# @admin.register(InflowMedia)
# class InflowMediaAdmin(admin.ModelAdmin):
#     list_display = ('name', 'order', 'file', 'is_complaint', 'related_product')
#     search_fields = ('name', 'order__order_id')
#
#
# @admin.register(InflowOrderHistory)
# class InflowOrderHistoryAdmin(admin.ModelAdmin):
#     list_display = ('order', 'event_type', 'timestamp', 'user', 'notes')
#     list_filter = ('event_type',)
#     search_fields = ('order__order_id', 'user__username')
#     readonly_fields = ('timestamp',)
