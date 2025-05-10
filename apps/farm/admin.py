from django.contrib import admin

from apps.farm.models import Farm, FarmProduct, FarmProductChangeLog, Farmer, Product, ProductChangeLog


class ProductChangeLogInline(admin.TabularInline):
    model = ProductChangeLog
    fields = ('event', 'field_name', 'old_value', 'new_value', 'date_created', 'created_by')
    readonly_fields = ('event', 'field_name', 'old_value', 'new_value', 'date_created', 'created_by')
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


class FarmProductChangeLogInline(admin.TabularInline):
    model = FarmProductChangeLog
    fields = ('event', 'field_name', 'old_value', 'new_value', 'date_created', 'created_by')
    readonly_fields = ('event', 'field_name', 'old_value', 'new_value', 'date_created', 'created_by')
    extra = 0
    can_delete = False

    def has_add_permission(self, request, obj=None):
        return False


# Inline for FarmChangeLog (commented model)
# class FarmChangeLogInline(admin.TabularInline):
#     model = FarmChangeLog
#     fields = ('event', 'field_name', 'old_value', 'new_value', 'date_created', 'created_by')
#     readonly_fields = ('event', 'field_name', 'old_value', 'new_value', 'date_created', 'created_by')
#     extra = 0
#     can_delete = False
#
#     def has_add_permission(self, request, obj=None):
#         """Disable adding new log entries."""
#         return False

# Inline for FarmerChangeLog (commented model)
# class FarmerChangeLogInline(admin.TabularInline):
#     model = FarmerChangeLog
#     fields = ('event', 'field_name', 'old_value', 'new_value', 'date_created', 'created_by')
#     readonly_fields = ('event', 'field_name', 'old_value', 'new_value', 'date_created', 'created_by')
#     extra = 0
#     can_delete = False
#
#     def has_add_permission(self, request, obj=None):
#         """Disable adding new log entries."""
#         return False

# Admin classes for main models

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    inlines = [ProductChangeLogInline]
    list_display = ('id', 'product_id', 'name', 'category', 'type', 'status', 'season_status', 'is_active')
    search_fields = ('name', 'description')
    list_filter = ('type', 'status', 'season_status')


@admin.register(FarmProduct)
class FarmProductAdmin(admin.ModelAdmin):
    inlines = [FarmProductChangeLogInline]
    list_display = ('id', 'product', 'farm', 'is_main_product', 'quantity', 'is_active')
    search_fields = ('product__name', 'farm__name')
    list_filter = ('is_main_product',)


@admin.register(Farm)
class FarmAdmin(admin.ModelAdmin):
    # inlines = [FarmChangeLogInline]  # Uncomment when FarmChangeLog is enabled
    list_display = ('id', 'name', 'farm_id', 'farm_type', 'location', 'size', 'is_active')
    search_fields = ('name', 'farm_id', 'location')
    list_filter = ('farm_type', 'land_ownership')


@admin.register(Farmer)
class FarmerAdmin(admin.ModelAdmin):
    # inlines = [FarmerChangeLogInline]  # Uncomment when FarmerChangeLog is enabled
    list_display = (
        'id', 'farmer_id', 'first_name', 'last_name', 'type',
        'gender', 'farm', 'phone_number', 'is_active'
    )
    search_fields = ('first_name', 'last_name', 'phone_number')
    list_filter = ('type', 'gender')
