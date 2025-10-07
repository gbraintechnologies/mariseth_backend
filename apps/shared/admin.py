from django import forms
from django.contrib import admin
from apps.shared.tasks import manager_tasks

from apps.shared.models import AppSetting, CustomType, District, Region, IntegrationLog

CATEGORY_NAME_CHOICES = [
    ('title', 'Title'),
    ('sender_id', 'Sender ID'),
    ('organization_domain', 'Organization Domain'),
    ('default_domain', 'Default Domain'),
    ('default_email', 'Default Email'),
    ('organization_email', 'Organization Email'),
    ('size_metric', 'Size Metric'),
    ('product_category', 'Product Category'),
    ('weight_metric', 'Weight Metric'),
    ('quantity_metric', 'Quantity Metric'),
]


class CustomTypeAdminForm(forms.ModelForm):
    category_name = forms.ChoiceField(choices=CATEGORY_NAME_CHOICES)

    class Meta:
        model = CustomType
        fields = '__all__'


@admin.register(CustomType)
class CustomTypeAdmin(admin.ModelAdmin):
    form = CustomTypeAdminForm
    list_display = (
        'id', 'name', 'category_name', 'organization',
        'date_created', 'date_modified', 'is_active', 'is_default',
        'is_hidden'
    )
    search_fields = ('name', 'category_name')


@admin.register(AppSetting)
class AppSettingAdmin(admin.ModelAdmin):
    list_display = ('organization', 'date_created', 'is_active')
    search_fields = ('organization__name', 'share_pricing', 'tax_value')


class DistrictInline(admin.TabularInline):
    model = District
    extra = 1
    ordering = ['id', 'name']


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'district_count')
    list_filter = ('code',)
    search_fields = ('name', 'code')
    ordering = ('name',)
    inlines = [DistrictInline]

    def district_count(self, obj):
        return obj.districts.count()

    district_count.short_description = 'Districts'


def resend_integration_logs(modeladmin, request, queryset):
    # Mapping of model names to their corresponding Celery sync tasks
    TASK_MAP = {
        'customer': manager_tasks.sync_customer_to_manager,
        'product': manager_tasks.sync_inventory_item_to_manager,
        'employee': manager_tasks.sync_employee_to_manager,
        'farm': manager_tasks.sync_supplier_to_manager,
        'infloworder': manager_tasks.sync_purchase_invoice_to_manager,
        'outfloworder': manager_tasks.sync_sales_invoice_to_manager,
    }

    logs_resent = 0
    for log in queryset:
        model_name = log.content_type.model
        task_to_run = TASK_MAP.get(model_name)

        if task_to_run:
            # Reset the log's status to PENDING before retrying
            log.status = IntegrationLog.Status.PENDING
            log.retry_count = 0  # Reset retry count
            log.error_message = "Manually resent from admin."
            log.save()

            # Asynchronously call the Celery task
            task_to_run.delay(log.id)
            logs_resent += 1
        else:
            # Handle cases where the model is not in our map
            modeladmin.message_user(
                request,
                f"Don't know how to resend log for model: {model_name}. No task mapped.",
                level='WARNING',
            )

    if logs_resent > 0:
        modeladmin.message_user(
            request,
            f"Successfully resent {logs_resent} integration log(s). They will be processed shortly.",
            level='SUCCESS',
        )
resend_integration_logs.short_description = "Resend selected integration logs for processing"


print("Loading IntegrationLogAdmin...")

@admin.register(IntegrationLog)
class IntegrationLogAdmin(admin.ModelAdmin):
    actions = [resend_integration_logs]
    # What to show in the list view (changelist)
    list_display = (
        '__str__', 
        'status', 
        'content_object_link', 
        'retry_count', 
        'date_created' # Assumes you have a 'created_at' field from BaseModel
    )
    
    # Fields to filter the list view by
    list_filter = (
        'status', 
        'content_type', 
        'retry_count'
    )
    
    # Fields to search across
    search_fields = (
        'object_id', 
        'error_message', 
        'payload_sent', 
        'response_received'
    )

    # Fields that should not be editable (everything, as it's a log)
    readonly_fields = (
        'content_type', 
        'object_id', 
        'content_object_link', 
        'status', 
        'payload_sent', 
        'response_received', 
        'error_message', 
        'retry_count', 
        'date_created', # Assumes this field exists
        'date_modified'  # Assumes this field exists
    )

    # How fields are grouped in the detail view
    fieldsets = (
        (None, {
            'fields': ('content_object_link', 'status', 'retry_count')
        }),
        ('Payloads & Responses', {
            # Use 'collapse' to make the large JSON fields less intrusive
            'classes': ('collapse',),
            'fields': ('payload_sent', 'response_received')
        }),
        ('Error Details', {
            'fields': ('error_message',)
        }),
    )

    # Custom method to display a link to the related object in the list view
    def content_object_link(self, obj):
        if obj.content_object:
            from django.urls import reverse
            from django.utils.html import format_html
            
            # Get the admin URL for the related object
            app_label = obj.content_type.app_label
            model_name = obj.content_type.model
            url = reverse(f'admin:{app_label}_{model_name}_change', args=[obj.object_id])
            
            # Return a clickable link
            return format_html('<a href="{}">{}</a>', url, obj.content_object)
        return "-"

    # Set the column header for the custom link
    content_object_link.short_description = 'Related Object'
    
    # Allow HTML rendering for the link
    content_object_link.allow_tags = True
