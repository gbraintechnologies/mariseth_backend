from typing import Optional

import boto3
import sentry_sdk
from botocore.exceptions import ClientError
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from base64 import encodebytes
from django.conf import settings

from mariseth.settings.base import ENVIRONMENT


class SESEmailClient:
    """Email client for sending emails using Amazon SES."""

    MAX_RECIPIENTS = 50  # SES limit for recipients per email

    def __init__(self):
        """Initialize the SES client using Django settings."""
        if ENVIRONMENT == 'local':
            self.client = boto3.client(
                'ses',
                region_name=settings.AWS_S3_REGION_NAME,
                aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY
            )
        else:
            self.client = boto3.client('ses')

    def send_email(
            self, sender: str,
            recipients: list,
            subject: str,
            body_text: str,
            body_html: str = None,
            attachments: list = None,
            bcc: Optional[list[str]] = None,
            cc: Optional[list[str]] = None
    ):
        """Send an email with optional HTML content and attachments, respecting SES recipient limits."""
        if ENVIRONMENT == 'production':
            subject_prefix = ''
        else:  # for development
            subject_prefix = f'[{ENVIRONMENT.upper()}] '

        all_recipients = recipients + (bcc if bcc else []) + (cc if cc else [])

        # Split recipients into batches of MAX_RECIPIENTS
        recipient_batches = [
            all_recipients[i:i + self.MAX_RECIPIENTS] for i in range(0, len(all_recipients), self.MAX_RECIPIENTS)
        ]

        responses = []
        for batch in recipient_batches:
            msg = MIMEMultipart('mixed')
            msg['Subject'] = subject_prefix + subject
            msg['From'] = sender
            msg['To'] = ', '.join(recipients[:self.MAX_RECIPIENTS])  # Set to the first batch's recipients
            if bcc:
                msg['Bcc'] = ', '.join(bcc[:self.MAX_RECIPIENTS])
            if cc:
                msg['Cc'] = ', '.join(cc[:self.MAX_RECIPIENTS])
            msg['ConfigurationSetName'] = 'scanport_email_logs'

            # Create a 'related' part to hold both plain and HTML versions
            alt_part = MIMEMultipart('alternative')
            msg.attach(alt_part)

            # Attach the text and HTML parts to the alternative part
            alt_part.attach(MIMEText(body_text, 'plain'))
            if body_html:
                alt_part.attach(MIMEText(body_html, 'html'))

            # Handle attachments
            if attachments:
                for filename, content_type, content in attachments:
                    content.seek(0)  # Reset the file pointer
                    part = MIMEApplication(content.read(), Name=filename)
                    part['Content-Disposition'] = f'attachment; filename="{filename}"'
                    part['Content-Type'] = content_type
                    part['Content-Transfer-Encoding'] = 'base64'
                    part.set_payload(encodebytes(content.getvalue()).decode())
                    msg.attach(part)

            try:
                # Send the email for this batch of recipients
                response = self.client.send_raw_email(
                    Source=sender,
                    Destinations=batch,
                    RawMessage={'Data': msg.as_string()}
                )
                responses.append(response)
            except ClientError as e:
                print(f'Failed to send email: {e}')
                sentry_sdk.capture_exception(e)
                raise e

        return responses
