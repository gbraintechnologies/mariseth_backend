import json

import requests
from decouple import config as env
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Send a test email to yourself using Amazon SES'

    def handle(self, *args, **options):
        api_key = env('FROG_SMS_API_KEY')
        username = env('FROG_SMS_USERNAME')

        headers = {
            'Content-Type': 'application/json',
            'API-KEY': api_key,
            'USERNAME': username
        }

        post_data = {
            "senderid": "PremierTech",
            "destinations": [
                {
                    "destination": "233545865156",
                    "msgid": "MGS1010101"
                }
            ],
            "message": "This is a sample message for SMS sending via FrogAPI.",
            "smstype": "text"
        }

        response = requests.post('https://frogapi.wigal.com.gh/api/v3/sms/send', headers=headers,
                                 data=json.dumps(post_data))

        print(response.json())
