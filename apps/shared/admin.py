from django import forms
from django.contrib import admin

from apps.shared.models import AppSetting, CustomType, District, Region

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
