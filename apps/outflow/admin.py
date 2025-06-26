from django.contrib import admin
from .models import (
    OutflowOrder,
    OutflowOrderPayments,
    OutflowOrderHistory,
    OutflowOrderWarehouse,
    OutflowOrderWarehouseProduct,
    OutflowOrderWarehouseImages,
    OutflowOrderWarehouseHistory,
    OutflowOrderDeliveryInformation,
    OutflowOrderDeliveryInformationWarehouse,
    OutflowOrderDeliveryInformationImage,
)


class OutflowOrderPaymentsInline(admin.TabularInline):
    model = OutflowOrderPayments
    extra = 0


class OutflowOrderHistoryInline(admin.TabularInline):
    model = OutflowOrderHistory
    extra = 0
    readonly_fields = ('field_name', 'old_value', 'new_value')


class OutflowOrderWarehouseInline(admin.TabularInline):
    model = OutflowOrderWarehouse
    extra = 0


class OutflowOrderDeliveryInformationInline(admin.TabularInline):
    model = OutflowOrderDeliveryInformation
    extra = 0


@admin.register(OutflowOrder)
class OutflowOrderAdmin(admin.ModelAdmin):
    inlines = [
        OutflowOrderPaymentsInline,
        OutflowOrderHistoryInline,
        OutflowOrderWarehouseInline,
        OutflowOrderDeliveryInformationInline,
    ]
    list_display = ('order_id', 'status', 'customer', 'total_quantity', 'total_cost')
    list_filter = ('status', 'customer')


class OutflowOrderWarehouseProductInline(admin.TabularInline):
    model = OutflowOrderWarehouseProduct
    extra = 0


class OutflowOrderWarehouseImagesInline(admin.TabularInline):
    model = OutflowOrderWarehouseImages
    extra = 0


class OutflowOrderWarehouseHistoryInline(admin.TabularInline):
    model = OutflowOrderWarehouseHistory
    extra = 0
    readonly_fields = ('field', 'old_value', 'new_value')


@admin.register(OutflowOrderWarehouse)
class OutflowOrderWarehouseAdmin(admin.ModelAdmin):
    inlines = [
        OutflowOrderWarehouseProductInline,
        OutflowOrderWarehouseImagesInline,
        OutflowOrderWarehouseHistoryInline,
    ]
    list_display = ('outflow_order', 'warehouse', 'total_quantity', 'total_cost', 'status')
    list_filter = ('status', 'warehouse')


class OutflowOrderDeliveryInformationWarehouseInline(admin.TabularInline):
    model = OutflowOrderDeliveryInformationWarehouse
    extra = 0


class OutflowOrderDeliveryInformationImageInline(admin.TabularInline):
    model = OutflowOrderDeliveryInformationImage
    extra = 0


@admin.register(OutflowOrderDeliveryInformation)
class OutflowOrderDeliveryInformationAdmin(admin.ModelAdmin):
    inlines = [
        OutflowOrderDeliveryInformationWarehouseInline,
        OutflowOrderDeliveryInformationImageInline,
    ]
    list_display = ('outflow_order', 'driver_name', 'driver_phone_number', 'destination')
