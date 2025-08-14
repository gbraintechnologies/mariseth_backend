from django.core.management.base import BaseCommand
from apps.shared.utils.email_client import EmailClient


class Command(BaseCommand):
    help = 'Send a test email using the EmailClient abstraction'

    def handle(self, *args, **options):
        email_client = EmailClient()

        sender = 'noreply@scaleforge.farm'
        recipients = ['okwesi73@gmail.com']
        subject = 'Hello from EmailClient'
        body_text = 'This is a test email from the abstracted EmailClient.'
        body_html = '<strong>This is a test email from the abstracted EmailClient.</strong>'

        response = email_client.send_email(
            sender=sender,
            recipients=recipients,
            subject=subject,
            body_text=body_text,
            body_html=body_html,
        )

        self.stdout.write(self.style.SUCCESS(f"Email sent! Response: {response}"))
