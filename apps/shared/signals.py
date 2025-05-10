from django.db.models.signals import pre_save
from django.dispatch import receiver

from apps.shared.models import AppSetting, AppSettingLog
from apps.shared.utils.current_user_middleware import get_current_user


@receiver(pre_save, sender=AppSetting)
def log_app_setting_changes(sender, instance, **kwargs):
    """Log changes to AppSetting model with config diffing."""
    user = get_current_user()
    if not instance.pk:  # Skip new instances
        return

    try:
        previous = AppSetting.objects.get(pk=instance.pk)
    except AppSetting.DoesNotExist:
        return

    changes = []
    numeric_fields = ['share_pricing', 'tax_value']

    # Track numeric field changes
    for field in numeric_fields:
        old_val = getattr(previous, field)
        new_val = getattr(instance, field)

        if old_val != new_val:
            changes.append(
                AppSettingLog(
                    app_setting=instance,
                    organization=instance.organization,
                    field=field,
                    previous_value=str(old_val),
                    current_value=str(new_val),
                    created_by=user
                )
            )

    # Track config changes with DeepDiff
    if previous.config != instance.config:
        changes.append(
            AppSettingLog(
                app_setting=instance,
                organization=instance.organization,
                field='config',
                config_diff=calculate_config_diff(previous.config, instance.config),
                created_by=user
            )
        )

    # Bulk create logs if changes exist
    if changes:
        AppSettingLog.objects.bulk_create(changes)


def calculate_config_diff(old_config, new_config):
    """
    Calculate the difference between two JSON objects (dictionaries).
    Returns a dictionary with added, removed, and changed keys.
    """
    diff = {
        'added': {},
        'removed': {},
        'changed': {}
    }

    # Check for added or changed keys
    for key in new_config:
        if key not in old_config:
            diff['added'][key] = new_config[key]
        elif old_config[key] != new_config[key]:
            if isinstance(old_config[key], dict) and isinstance(new_config[key], dict):
                # Recursively compare nested dictionaries
                nested_diff = calculate_config_diff(old_config[key], new_config[key])
                if nested_diff['added'] or nested_diff['removed'] or nested_diff['changed']:
                    diff['changed'][key] = nested_diff
            else:
                diff['changed'][key] = {
                    'old_value': old_config[key],
                    'new_value': new_config[key]
                }

    # Check for removed keys
    for key in old_config:
        if key not in new_config:
            diff['removed'][key] = old_config[key]

    return diff
