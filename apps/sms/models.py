from django.db import models

from apps.shared.models import BaseModel
from apps.sms.enums import SMSPurpose


class SMSLog(BaseModel):
    SMS_LOG_STATUS = (
        ('sent_to_provider', 'Sent To Provider'),
        ('failed', 'Failed'),
    )
    id = models.AutoField(primary_key=True)
    sender_id = models.CharField(max_length=120)
    to_number = models.CharField(max_length=120)
    status = models.CharField(max_length=120)
    provider = models.CharField(max_length=120,default="wireprick")
    purpose = models.CharField(max_length=120
                               , choices=[(purpose.value,purpose.value) for purpose in SMSPurpose]
                               , default=SMSPurpose.FARMER_REGISTRATION.value
                               )
    response_data = models.JSONField(
        null=True,
        blank=True,
    )