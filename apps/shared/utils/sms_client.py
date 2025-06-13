from typing import Optional

import sentry_sdk
from django.conf import settings

from apps.shared.utils.wirepick import send_wirepick_sms


class SMSClient:
    def __init__(self):
        self.provider = settings.SMS_PROVIDER.lower()

    def send_sms(
            self,
            phone_number: str,
            message: str,
            sender_id: Optional[str] = None,
            climsgid: Optional[str] = None,
            batchid: Optional[str] = None
    ):
        try:
            if self.provider == "wirepick":
                return send_wirepick_sms(phone_number, message, sender_id, climsgid, batchid)
            elif self.provider == "frog":
                pass
            else:
                raise ValueError(f"Unknown SMS provider: {self.provider}")
        except Exception as e:
            sentry_sdk.capture_exception(e)
            raise e
