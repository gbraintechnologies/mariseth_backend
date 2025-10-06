from django.db import models

from apps.shared.models import BaseModel


class Customer(BaseModel):
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE, related_name='customers')
    customer_id = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=255)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True, null=True)
    location = models.CharField(max_length=255, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    comments = models.TextField(blank=True, null=True)

    # NEW field to store the ID from the manager.io system
    manager_id = models.CharField(max_length=255,blank=True,null=True,unique=True,
        help_text="The unique key from the external Manager.io system."
    )
    manager_json_data = models.JSONField(
        null=True, blank=True, help_text="A cached copy of the last known data from Manager.io."
    )

    def __str__(self):
        return self.name