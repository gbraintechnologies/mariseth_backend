import uuid
import xml.etree.ElementTree as ET
from typing import Optional

import requests
from django.conf import settings

from mariseth.logging import logger


def send_wirepick_sms(
        phone_number: str,
        message: str,
        sender_id: Optional[str] = None,
        climsgid: Optional[str] = None,
        batchid: Optional[str] = None
):
    try:
        client_id = settings.WIREPICK_CLIENT_ID
        password = settings.WIREPICK_PASSWORD
        if sender_id is None:
            sender_id = getattr(settings, 'WIREPICK_SENDER_ID')

        if climsgid is None:
            climsgid = f"MSG{uuid.uuid4().hex[:8].upper()}"
        if batchid is None:
            batchid = f"BATCH{uuid.uuid4().hex[:4].upper()}"

        params = {
            'client': client_id,
            'password': password,
            'phone': phone_number,
            'text': message,
            'from': sender_id,
            'climsgid': climsgid,
            'batchid': batchid,
        }

        url = "https://api.wirepick.com/httpsms/send"
        response = requests.get(url, params=params)

        if response.status_code == 200:
            try:
                xml_response = ET.fromstring(response.content)
                sms_node = xml_response.find('sms')
                if sms_node is not None:
                    status = sms_node.findtext('status')
                    phone = sms_node.findtext('phone')
                    msgid = sms_node.findtext('msgid')

                    if status and status.lower() in ['accepted', 'submitted']:
                        logger.info(f"Wirepick SMS sent successfully to {phone} with status {status} and ID {msgid}")
                        return {
                            'status': status,
                            'message_id': msgid
                        }
                    else:
                        logger.error(f"Wirepick SMS failed: Status={status}, Phone={phone}")
                        return False
                else:
                    logger.error("Wirepick response XML missing <sms> element.")
                    return False
            except ET.ParseError:
                logger.error("Failed to parse XML response from Wirepick.")
                return False
        else:
            logger.error(f"Wirepick request failed. Status code: {response.status_code}, Response: {response.text}")
            return False

    except Exception as e:
        logger.error(f"Error sending Wirepick SMS: {str(e)}")
        return False
