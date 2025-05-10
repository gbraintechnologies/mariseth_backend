from django.contrib.auth import get_user_model
from django.db import models

from apps.shared.models import BaseModel

User = get_user_model()


class Organization(BaseModel):
    name = models.CharField(max_length=255)
    address = models.CharField(max_length=255)
    logo = models.ImageField(upload_to="organization/logo", null=True, blank=True)

    class Meta:
        verbose_name = "Organization"
        verbose_name_plural = "Organizations"

    def __str__(self):
        return self.name


class OrganizationUser(BaseModel):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organization_users')
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name='organization_users')

    class Meta:
        verbose_name = "Organization User"
        verbose_name_plural = "Organization Users"

    def __str__(self):
        return f"{self.user} - {self.organization}"

    def get_user_organization(self):
        return self.organization
