import uuid
import requests
from django.conf import settings
from mariseth.logging import logger


def send_frog_sms(phone_number, message):
    try:
        url = 'https://frogapi.wigal.com.gh/api/v3/sms/send'

        msg_id = f"MSG{uuid.uuid4().hex[:8].upper()}"

        headers = {
            'Content-Type': 'application/json',
            'API-KEY': settings.FROG_API_KEY,
            'USERNAME': settings.FROG_USERNAME
        }

        payload = {
            "senderid": settings.FROG_SENDER_ID,
            "destinations": [
                {
                    "destination": phone_number,
                    "msgid": msg_id
                }
            ],
            "message": message,
            "smstype": "text"
        }

        response = requests.post(url, json=payload, headers=headers)
        response_data = response.json()

        if response.status_code == 200 and response_data.get('status') == 'ACCEPTD':
            logger.info(f"SMS sent successfully to {phone_number} with message ID {msg_id}")
            return {
                'status': response_data['status'],
                'message_id': msg_id
            }
        else:
            logger.error(f"Failed to send SMS: {response_data}")
            return False

    except Exception as e:
        logger.error(f"Error sending SMS: {str(e)}")
        return False
