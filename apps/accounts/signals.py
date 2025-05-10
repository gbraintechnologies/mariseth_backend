from django.contrib.auth import get_user_model
from django.db.models.signals import pre_save
from django.dispatch import receiver

from apps.accounts.models import UserChangeLog
from apps.organizations.models import OrganizationUser

User = get_user_model()


@receiver(pre_save, sender=User)
def log_user_updates(sender, instance, **kwargs):
    if not instance.pk:
        return
    try:
        organization_user = OrganizationUser.objects.get(user=instance)
        organization = organization_user.organization
    except OrganizationUser.DoesNotExist:
        organization = None

    if instance.pk:
        try:
            old_instance = sender.objects.get(pk=instance.pk)
        except sender.DoesNotExist:
            return

        for field in instance._meta.fields:
            field_name = field.name
            old_value = getattr(old_instance, field_name)
            new_value = getattr(instance, field_name)

            if old_value != new_value:
                action = (
                    'delete' if field_name == 'is_active' and old_value is True and new_value is False else 'update'
                )

                UserChangeLog.objects.create(
                    user=instance,
                    organization=organization,
                    action=action,
                    field_name=field_name,
                    old_value=old_value,
                    new_value=new_value,
                )
