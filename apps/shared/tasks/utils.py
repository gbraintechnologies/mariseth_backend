import sentry_sdk
from celery import signals
from decouple import config as env
from django.conf import settings
from django.contrib.auth import get_user_model
from sentry_sdk.integrations.celery import CeleryIntegration

from apps.organizations.models import OrganizationUser
from apps.shared.literals import DEFAULT_EMAIL
from apps.shared.models import CustomType

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
        return organization_email.name if organization_email else DEFAULT_EMAIL
    except CustomType.DoesNotExist:
        return DEFAULT_EMAIL


