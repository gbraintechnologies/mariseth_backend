from django.contrib import admin

from apps.accounting.models import Expense


@admin.register(Expense)
class ExpenseAdmin(admin.ModelAdmin):
    list_display = ('id', 'order_type', 'order', 'amount', 'description', 'date_created')
    list_filter = ('order_type', 'date_created')
    search_fields = ('description',)
    readonly_fields = ('date_created',)
