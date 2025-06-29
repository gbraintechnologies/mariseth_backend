from celery import shared_task

from apps.organizations.models import OrganizationUser
from apps.shared.tasks.utils import get_organization_default_sender_id
from apps.shared.utils.sms_client import SMSClient


@shared_task
def send_verification_sms(user_id, phone_number, verification_code):
    organization = OrganizationUser.objects.get(user_id=user_id).organization
    message = (
        f"Your Mariseth verification code is: {verification_code}\n"
        f"Use this code to complete your registration. "
        f"The code expires in 10 minutes."
    )
    sender_id = get_organization_default_sender_id(organization)
    client = SMSClient()
    result = client.send_sms(
        phone_number=phone_number,
        message=message,
        sender_id=sender_id
    )

    if not result:
        from sentry_sdk import capture_message
        capture_message(f"Failed to send verification SMS to {phone_number}")
