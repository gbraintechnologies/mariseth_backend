from decimal import Decimal

from django.db import models
from apps.ussd.enums import UssdSteps, UssdFlowType
from apps.shared.models import BaseModel

class UssdSession(BaseModel):
    phone_number = models.CharField(max_length=20, db_index=True)
    session_id = models.CharField(max_length=100, unique=True)
    current_step = models.CharField(
        max_length=100,
        choices=[(step.value, step.value) for step in UssdSteps],
        default=UssdSteps.USSD_INIT.value
    )
    flow_type = models.CharField(
        max_length=100,
        choices=[(step.value, step.value) for step in UssdFlowType],
        default=UssdFlowType.USSD_INIT.value
    )
    payload = models.JSONField(default=dict, blank=True)
    date_created = models.DateTimeField(auto_now_add=True)
    date_modified = models.DateTimeField(auto_now_add=True)
    history = models.JSONField(default=list)
    page_number = models.PositiveIntegerField(default=1)
    page_size = models.PositiveIntegerField(default=10)
    expires_at = models.DateTimeField(auto_now_add=True)


    def __str__(self):
        return f"{self.phone_number} - {self.session_id}"