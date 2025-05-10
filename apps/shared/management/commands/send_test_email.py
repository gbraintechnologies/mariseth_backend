from django.core.management.base import BaseCommand

from apps.shared.utils.email_client import SESEmailClient


class Command(BaseCommand):
    help = 'Send a test email to yourself using Amazon SES'

    def handle(self, *args, **options):
        email_client = SESEmailClient()

        # Define the email parameters
        sender = 'okwesi73@gmail.com'  # Make sure this is verified in SES
        recipients = ['gyamfiowusu630@gmail.com']  # The recipient email address
        subject = 'Hello from SES'
        body_text = 'Hello, this is my first email sent through Amazon SES using Django!'
        body_html = '<h1>Hello, this is my first email sent through Amazon SES using Django!</h1>'

        # Call the send_bulk_email method to send the email
        response = email_client.send_email(
            sender=sender,
            recipients=recipients,
            subject=subject,
            body_text=body_text,
            body_html=body_html
        )

        self.stdout.write(self.style.SUCCESS('Successfully sent email! Response:', response))
