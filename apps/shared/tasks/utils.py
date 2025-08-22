import sentry_sdk
from celery import signals
from decouple import config as env
from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from sentry_sdk.integrations.celery import CeleryIntegration

from apps.credit.models import Credit
from apps.hr.models import LeaveRequest
from apps.organizations.models import OrganizationUser
from apps.shared.models import CustomType
from mariseth.celery import app

User = get_user_model()


@signals.celeryd_init.connect
def init_sentry(**kwargs):
    sentry_sdk.init(
        dsn=env('SENTRY_DSN'),
        integrations=[CeleryIntegration(monitor_beat_tasks=True)],
        environment=env('ENVIRONMENT'),
        release="v1.0",
    )


def get_organization_domain(user):
    """
    Returns the domain name based on environment or organization configuration.
    """
    if settings.ENVIRONMENT == "local":
        return "localhost:8000"
    else:
        try:
            organization_domain = OrganizationUser.objects.get(user=user).organization.customtype_set.get(
                category_name='organization_domain', is_hidden=True
            )
            return organization_domain.name
        except (User.DoesNotExist, CustomType.DoesNotExist):
            default_domain = CustomType.objects.get(
                category_name='default_domain', is_hidden=True
            )
            return default_domain.name


def get_organization_email(organization):
    """
    Returns the organization's email address for sending emails.
    """
    try:
        organization_email = organization.customtype_set.filter(
            category_name='organization_email',
            is_active=True,
            is_default=True
        ).order_by('-date_created').first()
        return organization_email.name if organization_email else "noreply@scaleforge.farm"
    except CustomType.DoesNotExist:
        return "noreply@scaleforge.farm"


def get_organization_default_sender_id(organization):
    """
    Returns the organization's sender_id address for sending emails.
    """
    try:
        organization_sms = organization.customtype_set.filter(
            category_name='sender_id',
            is_active=True,
            is_default=True
        ).order_by('-date_created').first()
        return organization_sms.name if organization_sms else "LOGICIEL"
    except CustomType.DoesNotExist:
        return "LOGICIEL"


@app.task(bind=True)
def update_overdue_credits(self) -> None:
    print("------Updating overdue credits-----")
    today = timezone.localdate()
    updates = Credit.objects.filter(
        due_date__lt=today,
        payment_status__in=['active', 'partial']
    ).update(payment_status='overdue')
    print("------Overdue credits updated-----")


@app.task(bind=True)
def update_completed_leaves(self) -> None:
    print("------Updating completed leaves-----")
    today = timezone.localdate()
    updates = LeaveRequest.objects.filter(
        end_date__lt=today,
        status='approved'
    ).update(status='completed')
    print(f"------Completed leaves updated: {updates}-----")