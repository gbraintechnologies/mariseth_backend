import requests
import sentry_sdk
from typing import Optional
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from django.conf import settings
from mariseth.settings.base import ENVIRONMENT


class ZeptoMailClient:
    """Email client for sending emails using Zoho ZeptoMail."""

    MAX_RECIPIENTS = 50
    API_URL = "https://api.zeptomail.com/v1.1/email"

    def __init__(self):
        """Initialize the ZeptoMail client with API key from settings."""
        self.api_key = settings.ZEPTO_MAIL_API_KEY

    def send_email(
        self,
        sender: str,
        recipients: list,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        bcc: Optional[list[str]] = None,
        cc: Optional[list[str]] = None,
    ):
        """Send an email with optional HTML content, CC, and BCC."""
        subject_prefix = '' if ENVIRONMENT == 'production' else f'[{ENVIRONMENT.upper()}] '

        # Combine recipients
        all_recipients = recipients + (bcc or []) + (cc or [])

        # Split recipients into batches
        recipient_batches = [
            all_recipients[i:i + self.MAX_RECIPIENTS] for i in range(0, len(all_recipients), self.MAX_RECIPIENTS)
        ]
        responses = []
        for batch in recipient_batches:
            print("batch", batch)
            payload = {
                "from": {"address": sender},
                "to": [{"email_address": {"address": r}} for r in recipients],
                "subject": subject_prefix + subject,
                "textbody": body_text,
            }

            if body_html:
                payload["htmlbody"] = body_html

            if cc:
                payload["cc"] = [{"email_address": {"address": r}} for r in cc]

            if bcc:
                payload["bcc"] = [{"email_address": {"address": r}} for r in bcc]

            headers = {
                "accept": "application/json",
                "content-type": "application/json",
                "authorization": f"{self.api_key}",
            }

            try:
                response = requests.post(self.API_URL, json=payload, headers=headers)
                response.raise_for_status()
                responses.append(response.json())
            except requests.RequestException as e:
                print(f"Failed to send email: {e}")
                sentry_sdk.capture_exception(e)
                raise e

        return responses
