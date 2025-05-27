import xml.etree.ElementTree as ET
from urllib.parse import urlencode

import requests
from decouple import config as env
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Send a test SMS using the Wirepick HTTP API'

    def handle(self, *args, **options):
        client_id = env('WIREPICK_CLIENT_ID')
        password = env('WIREPICK_PASSWORD')
        sender_id = 'LOGICIEL'
        phone = '233545865156'
        message = 'This is a sample message sent using Wirepick.'
        climsgid = 'MSG12345'
        batchid = 'BATCH001'

        # Build query parameters
        params = {
            'client': client_id,
            'password': password,
            'phone': phone,
            'text': message,
            'from': sender_id,
            'climsgid': climsgid,
            'batchid': batchid,
        }

        # Encode URL and make the request
        url = f'https://api.wirepick.com/httpsms/send?{urlencode(params)}'
        response = requests.get(url)

        # Handle XML response
        if response.status_code == 200:
            try:
                xml_response = ET.fromstring(response.content)
                for sms in xml_response.findall('sms'):
                    msgid = sms.findtext('msgid')
                    phone_number = sms.findtext('phone')
                    status = sms.findtext('status')
                    self.stdout.write(self.style.SUCCESS(
                        f'SMS to {phone_number} submitted successfully. Status: {status}, MsgID: {msgid}'
                    ))
            except ET.ParseError:
                self.stderr.write('Failed to parse XML response from Wirepick.')
        else:
            self.stderr.write(f'Failed to send SMS. Status code: {response.status_code}, Response: {response.text}')
