from django.contrib import admin

from .models import Credit, CreditChangeLog, CreditPayback, InputCredit, InputCreditPurchase, CreditWarehouse


class CreditWarehouseInline(admin.TabularInline):
    model = CreditWarehouse
    extra = 0
    fields = ('input_credit', 'warehouse', 'quantity', 'is_fulfilled')
    readonly_fields = ('is_fulfilled',)




class CreditPaybackInline(admin.TabularInline):
    model = CreditPayback
    extra = 0
    can_delete = False
    fields = (
        'payback_method', 'amount', 'outstanding_before', 'outstanding_after', 'date_paid', 'status', 'date_created',
        'created_by'
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class CreditChangeLogInline(admin.TabularInline):
    model = CreditChangeLog
    extra = 0
    can_delete = False
    fields = ('payback', 'field_name', 'event', 'old_value', 'new_value', 'notes', 'date_created')
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Credit)
class CreditAdmin(admin.ModelAdmin):
    inlines = [CreditPaybackInline, CreditChangeLogInline, CreditWarehouseInline]
    list_display = (
        'id', 'credit_id', 'input_credit', 'farmer', 'credit_amount',
        'issue_date', 'due_date', 'payment_status',
        'approval_status', 'is_active'
    )
    search_fields = ('farmer__name', 'id', 'main_crops')
    list_filter = ('approval_status', 'payment_status')
    fieldsets = (
        ('Basic Info', {'fields': ('farmer', 'input_credit', 'quantity', 'quantity_metric')}),
        ('Financials', {'fields': ('credit_amount', 'interest_rate', 'outstanding_amount', 'issue_date', 'due_date')}),
        ('Status', {'fields': ('payment_status', 'approval_status', 'denial_notes', 'main_crops')}),
        ('Notes', {'fields': ('notes',), 'classes': ('collapse',)}),
    )


@admin.register(InputCredit)
class InputCreditAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'category', 'price', 'quantity', 'weight', 'is_active')
    search_fields = ('name',)
    list_filter = ('category',)


@admin.register(InputCreditPurchase)
class InputCreditPurchaseAdmin(admin.ModelAdmin):
    list_display = ('id', 'input_credit', 'purchase_date', 'quantity', 'total_price', 'total_weight', 'is_active')
    search_fields = ('input_credit__name',)
    list_filter = ('purchase_date',)
