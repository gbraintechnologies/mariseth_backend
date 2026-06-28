import os

import requests
from celery import shared_task

from apps.sms.enums import SMSPurpose
from apps.sms.models import SMSLog

SMS_API_URL = os.getenv("SMS_API_URL")
SMS_API_KEY = os.getenv("SMS_API_KEY")
SMS_SENDER_ID = os.getenv("SMS_SENDER_ID")

@shared_task
def send_sms(phone, message, purpose = SMSPurpose.FARMER_REGISTRATION):
    data = {
        "phone": phone,
        "text": message,
        "from": SMS_SENDER_ID,
    }
    headers = {
        "Content-Type": "application/json",
        "wpkKey": SMS_API_KEY,
    }
    url = f"{SMS_API_URL}/sendsms"
    response = requests.post(url, json=data,headers=headers)
    status = "sent_to_provider" if response.status_code == 200 else "failed"
    SMSLog.objects.create(
        sender_id=SMS_SENDER_ID,
        to_number=phone,
        purpose=purpose,
        status=status,
        response_data=response.json()
    )