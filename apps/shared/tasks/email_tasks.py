import sentry_sdk
from celery import shared_task
from django.contrib.auth import get_user_model
from django.template.loader import get_template

from apps.organizations.models import OrganizationUser
from apps.shared.tasks.utils import get_organization_domain, get_organization_email
from apps.shared.utils.email_client import SESEmailClient
from mariseth.logging import logger

User = get_user_model()


@shared_task
def send_verification_email(verification_code, template_name, user):
    try:
        user = User.objects.get(pk=user)
        organization_user = OrganizationUser.objects.get(user=user)

        domain = get_organization_domain(user)
        context = {
            'user_fullname': user.get_full_name(),
            'verification_code': verification_code,
            'user_email': user.email,
            'domain': domain,
        }
        template = get_template(template_name)
        email_template = template.render(context)
        email = get_organization_email(organization_user.organization)

        sender = f'{organization_user.organization.name} <{email}>'
        to_email = [user.email]
        subject = f'Verification Code for {user.get_full_name()}'
        body_html = email_template
        body_text = f'Verification Code: {verification_code}'

        if to_email:
            email_client = SESEmailClient()
            response = email_client.send_email(
                sender=sender, recipients=to_email,
                subject=subject, body_html=body_html,
                body_text=body_text
            )
            logger.info(f"Email sent successfully {response}")
        else:
            logger.error('No email address provided.')

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Error sending verification email: {str(e)}")
        raise

from django.utils import timezone

from apps.credit.models import Credit
from mariseth.celery import app


@app.task(bind=True)
def update_overdue_credits(self) -> None:
    print("------Updating overdue credits-----")
    today = timezone.localdate()
    updates = Credit.objects.filter(
        due_date__lt=today,
        payment_status__in=['active', 'partial']
    ).update(payment_status='overdue')
    print(f"------Overdue credits updated-----")
