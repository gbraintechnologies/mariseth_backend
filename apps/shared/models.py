import base64

from decouple import config as env
from django.db import models
from django.utils import timezone
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


def xor_cipher(input_str, key):
    """
    Encrypt or decrypt a string using XOR and a key.
    """
    return ''.join(chr(ord(c) ^ ord(key[i % len(key)])) for i, c in enumerate(input_str))


def base64_encode(input_str):
    """
    Encode input string with Base64.
    """
    # Convert to bytes, encode, then convert back to string for database compatibility
    return base64.b64encode(input_str.encode()).decode('utf-8')


class BaseModel(models.Model):
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'accounts.User',
        null=True,
        on_delete=models.SET_NULL,
        blank=True,
        related_name='created_%(class)ss'
    )
    date_deleted = models.DateTimeField(null=True, blank=True)
    deleted_by = models.ForeignKey(
        'accounts.User',
        blank=True,
        null=True,
        on_delete=models.SET_NULL,
        related_name='deleted_%(class)ss'
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True

    def soft_delete(self, owner, fields_to_encrypt: list = None):
        """
        Soft delete by setting is_active to False.
        """
        self.is_active = False
        self.deleted_by = owner
        self.date_deleted = timezone.now()

        if fields_to_encrypt is not None:
            obj_id_str = str(self.id)
            secret_key = env('SECRET_KEY')
            key = f'{secret_key}{obj_id_str}'
            for field in fields_to_encrypt:
                if hasattr(self, field):
                    value = getattr(self, field) or ''
                    encrypted_value = base64_encode(xor_cipher(value + obj_id_str, key))
                    setattr(self, field, encrypted_value)
            if hasattr(self, 'user'):
                self.user = None
        self.save()


class CustomType(BaseModel):
    name = models.CharField(max_length=50)
    category_name = models.CharField(max_length=50)
    description = models.CharField(max_length=255, blank=True, null=True)
    category_type = models.CharField(max_length=255, blank=True, null=True)
    is_default = models.BooleanField(default=False)
    is_hidden = models.BooleanField(default=False)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = 'Custom Type'
        verbose_name_plural = 'Custom Types'

    def __str__(self):
        return f"{self.name} ({self.category_name})"


class AppSetting(BaseModel):
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    config = models.JSONField(default=dict, blank=True, null=True)

    class Meta:
        verbose_name = 'App Setting'
        verbose_name_plural = 'App Settings'

    def __str__(self):
        return f"{self.organization.name}"


class AppSettingLog(BaseModel):
    app_setting = models.ForeignKey('AppSetting', on_delete=models.CASCADE, related_name='logs')
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    previous_value = models.CharField(max_length=255, blank=True, null=True)
    current_value = models.CharField(max_length=255, blank=True, null=True)
    config_diff = models.JSONField(blank=True, null=True)
    field = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = 'App Setting Log'
        verbose_name_plural = 'App Setting Logs'



class Region(models.Model):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=4, unique=True)
    id = models.BigIntegerField(primary_key=True)

    def __str__(self):
        return self.name

class District(models.Model):
    name = models.CharField(max_length=100)
    region = models.ForeignKey(Region, related_name='districts', on_delete=models.CASCADE)
    id = models.BigIntegerField(primary_key=True)
    class Meta:
        unique_together = ('name', 'region')

    def __str__(self):
        return self.name


class Help(BaseModel):
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    description = models.TextField()
    url = models.URLField()

    def __str__(self):
        return self.title


class IntegrationLog(BaseModel):
    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending"
        SUCCESS = "SUCCESS", "Success"
        FAILED = "FAILED", "Failed"

    # A generic link to ANY model in our project (Customer, Supplier, etc.)
    content_type = models.ForeignKey(ContentType, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey("content_type", "object_id")

    # Status and debugging info
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.PENDING, db_index=True
    )
    payload_sent = models.JSONField(null=True, blank=True, help_text="The exact JSON payload sent to the API.")
    response_received = models.JSONField(null=True, blank=True, help_text="The full response from the API.")
    error_message = models.TextField(blank=True, null=True, help_text="Details of the last error.")
    retry_count = models.PositiveSmallIntegerField(default=0)


    def __str__(self):
        return f"Integration for {self.content_type.model} #{self.object_id} - {self.status}"
