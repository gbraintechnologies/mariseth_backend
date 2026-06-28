from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.validators import MinLengthValidator
from django.db import models

from apps.shared.literals import DECREASE_QUANTITY_STRING, INCREASE_QUANTITY_STRING, UPDATE_FIELD_STRING
from apps.shared.models import BaseModel, CustomType
from apps.shared.utils.validators import validate_only_digits

User = get_user_model()


class Farm(BaseModel):
    FARM_TYPE_CHOICES = (
        ('internal', 'Internal'),
        ('external', 'External')
    )

    LAND_OWNERSHIP_CHOICES = (
        ('owned', 'Owned'),
        ('leased', 'Leased'),
        ('communal', 'Communal'),
        ('other', 'Other')
    )

    organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True)
    farm_id = models.CharField(max_length=50, unique=True)
    user = models.ForeignKey('accounts.User', on_delete=models.CASCADE, related_name='farms', null=True, blank=True)
    farm_type = models.CharField(max_length=20, choices=FARM_TYPE_CHOICES)
    type = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=100, null=True, blank=True)
    location = models.CharField(max_length=255, null=True, blank=True)
    region = models.ForeignKey('shared.Region', related_name='farms', on_delete=models.SET_NULL, null=True, blank=True)
    district = models.ForeignKey('shared.District', related_name='farms', on_delete=models.SET_NULL, null=True,
                                 blank=True)
    size = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    size_metric = models.ForeignKey(CustomType, on_delete=models.SET_NULL, null=True,
                                    related_name='farm_size_metrics')
    livestock_kept = models.CharField(max_length=255, blank=True, null=True)
    has_access_to_market = models.BooleanField(default=False)
    irrigation = models.BooleanField(default=False, blank=True, null=True)
    use_of_fertilizers = models.JSONField(default=list, blank=True, null=True)
    farming_methods = models.JSONField(default=list, blank=True, null=True)
    provide_training = models.BooleanField(default=False)
    government_ngo_support = models.BooleanField(default=False)
    specify_support = models.CharField(max_length=255, blank=True, null=True)
    areas_of_assistance = models.JSONField(default=list, blank=True, null=True)
    farmer = models.ForeignKey('Farmer', on_delete=models.CASCADE, related_name='owned_farms', null=True, blank=True)
    land_ownership = models.CharField(max_length=20, choices=LAND_OWNERSHIP_CHOICES)
    other_specification = models.CharField(max_length=255, blank=True, null=True)

    # -- Manager.io Integration Fields --
    manager_id = models.CharField(max_length=255, blank=True, null=True, unique=True,
                                  help_text="The unique key from the external Manager.io system."
                                  )
    manager_json_data = models.JSONField(
        null=True, blank=True, help_text="A cached copy of the last known data from Manager.io."
    )

    def __str__(self):
        return f"{self.id} - {self.name}"


# class FarmChangeLog(BaseModel):
#     farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name='change_logs')
#     organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True,
#                                      related_name='farm_change_logs')
#     event = models.CharField(max_length=50)
#     field_name = models.CharField(max_length=255, null=True, blank=True)
#     old_value = models.TextField(null=True, blank=True)
#     new_value = models.TextField(null=True, blank=True)
#
#     def __str__(self):
#         return f'FarmChangeLog({self.farm.name}, {self.event}, {self.field_name})'


class Farmer(BaseModel):
    FARMER_TYPE_CHOICES = (
        ('lead', 'Lead Farmer'),
        ('smallholder', 'Small Holder')
    )

    GENDER_CHOICES = (
        ('m', 'Male'),
        ('f', 'Female')
    )

    organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True)
    user = models.OneToOneField('accounts.User', on_delete=models.CASCADE, related_name='farmer', null=True, blank=True)
    farmer_id = models.CharField(max_length=50, unique=True)
    type = models.CharField(max_length=20, choices=FARMER_TYPE_CHOICES)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    other_names = models.CharField(max_length=100, blank=True, null=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    id_type = models.CharField(max_length=50, null=True, blank=True)
    id_number = models.CharField(max_length=50, null=True, blank=True)
    phone_number = models.CharField(unique=True, max_length=40, blank=False, null=True,
                                    validators=[
                                        MinLengthValidator(
                                            11, "Phone number number must be at least 11 characters."),
                                        validate_only_digits],
                                    )
    email = models.EmailField(unique=True, null=True, blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    village = models.CharField(max_length=100, null=True, blank=True)
    region = models.ForeignKey('shared.Region', related_name='farmers', on_delete=models.SET_NULL, null=True,
                               blank=True)
    district = models.ForeignKey('shared.District', related_name='farmers', on_delete=models.SET_NULL, null=True,
                                 blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    farm = models.ForeignKey(Farm, on_delete=models.SET_NULL, null=True, blank=True, related_name='farmers')
    lead_farmer = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name='smallholder_farmers')
    leadership_experience = models.JSONField(null=True, blank=True)
    support_assistance = models.JSONField(null=True, blank=True)
    farmer_reg_request = models.OneToOneField('FarmerRegistrationRequest', on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.id} - {self.first_name} {self.last_name}"

    def soft_delete(self, owner, fields_to_encrypt: list = None):
        """
        Soft delete the farmer and cascade the soft delete to the linked user.
        """
        super().soft_delete(owner=owner, fields_to_encrypt=fields_to_encrypt)
        if self.user_id and self.user.is_active:
            self.user.soft_delete(owner=owner, fields_to_encrypt=['email', 'phone_number', 'username'])

class FarmerRegistrationRequest(BaseModel):
    REQUEST_CHANNELS = (
        ("USSD", "USSD"),
    )
    STATUS_CHOICES = (
        ("pending", "Pending"),
        ("approved", "Approved"),
        ("rejected", "Rejected"),
    )
    id = models.AutoField(primary_key=True)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True)
    phone_number = models.CharField(max_length=100, blank=True, null=True)
    id_type = models.CharField(max_length=50, null=True, blank=True)
    id_number = models.CharField(max_length=50, null=True, blank=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    gender = models.CharField(max_length=1, choices=Farmer.GENDER_CHOICES)
    other_names = models.CharField(max_length=100, blank=True, null=True)
    request_channel = models.CharField(
        max_length=100,
        choices=REQUEST_CHANNELS,
        default="USSD",
    )
    country = models.CharField(max_length=100, null=True, blank=True)
    region = models.ForeignKey('shared.Region', on_delete=models.SET_NULL, null=True,
                               blank=True)
    district = models.ForeignKey('shared.District', on_delete=models.SET_NULL, null=True,
                                 blank=True)
    address = models.CharField(max_length=255, null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    comments = models.TextField(blank=True, null=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey('accounts.User', on_delete=models.SET_NULL, null=True, blank=True, )
    reviewed_at = models.DateTimeField(null=True, blank=True)

class FarmerDocument(BaseModel):
    farmer = models.ForeignKey('Farmer', related_name='documents', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField(blank=True, null=True)
    document = models.FileField(upload_to='farmer_documents/', null=True, blank=True)

    class Meta:
        verbose_name = "Farmer Document"
        verbose_name_plural = "Farmer Documents"

    def __str__(self):
        return f"{self.title} for {self.farmer.first_name} {self.farmer.last_name}"


# class FarmerChangeLog(BaseModel):
#     farmer = models.ForeignKey(Farmer, on_delete=models.CASCADE, related_name='change_logs')
#     organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True,
#                                      related_name='farmer_change_logs')
#     event = models.CharField(max_length=50)
#     field_name = models.CharField(max_length=255, null=True, blank=True)
#     old_value = models.TextField(null=True, blank=True)
#     new_value = models.TextField(null=True, blank=True)
#
#     def __str__(self):
#         return f'FarmerChangeLog({self.farmer.first_name} {self.farmer.last_name}, {self.event}, {self.field_name})'


class Product(BaseModel):
    PRODUCT_TYPE_CHOICES = (
        ('crop', 'Crop'),
        ('other', 'Other')
    )

    PRODUCT_SEASON_CHOICES = (
        ('in', 'In Season'),
        ('out', 'Out of Season')
    )

    PRODUCT_STATUS_CHOICES = (
        ('active', 'Active'),
        ('inactive', 'Inactive')
    )

    organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True)
    product_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    category = models.ForeignKey(CustomType, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name='product_categories', )
    last_updated = models.DateField(auto_now=True)
    weight = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)  # weight of one product
    weight_metric = models.ForeignKey(CustomType, on_delete=models.SET_NULL, null=True, blank=True,
                                      related_name='product_weight_metrics')
    quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True,
                                   blank=True)  # total quantity in all warehouses
    quantity_metric = models.ForeignKey(CustomType, on_delete=models.SET_NULL, null=True, blank=True,
                                        related_name='product_quantity_metrics', )
    type = models.CharField(max_length=20, choices=PRODUCT_TYPE_CHOICES)
    season_status = models.CharField(max_length=10, choices=PRODUCT_SEASON_CHOICES, null=True, blank=True)
    status = models.CharField(max_length=10, choices=PRODUCT_STATUS_CHOICES, default='active')
    season_start = models.DateField(null=True, blank=True)
    season_end = models.DateField(null=True, blank=True)
    description = models.TextField(blank=True, null=True)
    breed = models.CharField(max_length=100, blank=True, null=True)
    color = models.CharField(max_length=100, blank=True, null=True)

    # -- Manager.io Integration Fields --
    manager_id = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        unique=True,
        help_text="The unique key from the external Manager.io system."
    )
    manager_json_data = models.JSONField(
        null=True, blank=True, help_text="A cached copy of the last known data from Manager.io."
    )

    def __str__(self):
        return f"{self.id} - {self.name}"

    def add_quantity(self, quantity):
        self.quantity = (self.quantity or Decimal(0)) + Decimal(quantity)
        self.save()

    def remove_quantity(self, quantity):
        quantity = Decimal(quantity)
        if self.quantity >= quantity:
            self.quantity -= quantity
            self.save()
        else:
            raise ValueError("Insufficient global stock")


class ProductChangeLog(BaseModel):
    EVENT_CHOICES = (
        (UPDATE_FIELD_STRING, 'Update Field'),
        (INCREASE_QUANTITY_STRING, 'Increase Quantity'),
        (DECREASE_QUANTITY_STRING, 'Decrease Quantity')
    )

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='change_logs')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='product_change_logs')
    event = models.CharField(max_length=50, choices=EVENT_CHOICES)
    field_name = models.CharField(max_length=255, null=True, blank=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    def __str__(self):
        return f'ProductChangeLog({self.product.name}, {self.event}, {self.field_name})'


class FarmProduct(BaseModel):
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE)
    is_main_product = models.BooleanField(default=False)
    quantity = models.IntegerField(null=True, blank=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        unique_together = ('product', 'farm')


class FarmProductChangeLog(BaseModel):
    EVENT_CHOICES = (
        (UPDATE_FIELD_STRING, 'Update Field'),
        (INCREASE_QUANTITY_STRING, 'Increase Quantity'),
        (DECREASE_QUANTITY_STRING, 'Decrease Quantity')
    )
    farm_product = models.ForeignKey(FarmProduct, on_delete=models.CASCADE, related_name='change_logs')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='farm_product_change_logs')
    event = models.CharField(max_length=50)
    field_name = models.CharField(max_length=255, null=True, blank=True)
    old_value = models.TextField(null=True, blank=True)
    new_value = models.TextField(null=True, blank=True)

    def __str__(self):
        return (f'FarmProductChangeLog(Farm: {self.farm_product.farm.name}, Product: {self.farm_product.product.name},'
                f' {self.event}, {self.field_name})')
