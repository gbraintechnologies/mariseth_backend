import base64

from decouple import config as env
from django.db import models
from django.utils import timezone


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
                    value = getattr(self, field)
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


