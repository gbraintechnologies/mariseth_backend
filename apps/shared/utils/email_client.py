from typing import Optional

import sentry_sdk
from django.conf import settings
from apps.shared.utils.sendgrid import sendgrid_send_email
from apps.shared.utils.zepto_mail import ZeptoMailClient


class EmailClient:
    def __init__(self):
        self.provider = settings.EMAIL_PROVIDER.lower()

    def send_email(
            self,
            sender: str,
            recipients: list[str],
            subject: str,
            body_text: str,
            body_html: Optional[str] = None,
            attachments: Optional[list] = None,
            bcc: Optional[list[str]] = None,
            cc: Optional[list[str]] = None
    ):
        try:
            if self.provider == "sendgrid":
                return sendgrid_send_email(sender, recipients, subject, body_text, body_html, attachments, bcc, cc)
            elif self.provider == "zepto_mail":
                return ZeptoMailClient().send_email(sender, recipients, subject, body_text, body_html, bcc, cc)
            elif self.provider == "mailgun":
                raise NotImplementedError("Mailgun provider is not implemented yet.")
                # return mailgun_send_email(...)
            elif self.provider == "ses":
                raise NotImplementedError("SES provider is not implemented yet.")
                # return ses_send_email(...)
            else:
                raise ValueError(f"Unknown email provider: {self.provider}")
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise e
