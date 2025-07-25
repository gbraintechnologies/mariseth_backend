from django.contrib.contenttypes.models import ContentType
from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounting.models import Expense
from apps.inflow.models import InflowOrder
from apps.outflow.models import OutflowOrder


@receiver(post_save, sender=InflowOrder)
def create_or_update_expense_from_inflow(sender, instance, created, **kwargs):
    if instance.status == 'approved' and instance.additional_cost_amount > 0 :
        expense_data = {
            'order_type': 'inflow',
            'amount': instance.additional_cost_amount,
            'description': instance.additional_costs,
        }
        Expense.objects.update_or_create(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.pk,
            defaults=expense_data
        )
    elif instance.additional_cost_amount == 0:
        # If additional_cost_amount is 0, delete any existing Expense record for this order
        Expense.objects.filter(content_type=ContentType.objects.get_for_model(instance), object_id=instance.pk).delete()


@receiver(post_save, sender=OutflowOrder)
def create_or_update_expense_from_outflow(sender, instance, created, **kwargs):
    if instance.status == 'complete' and instance.additional_cost_amount > 0:
        expense_data = {
            'order_type': 'outflow',
            'amount': instance.additional_cost_amount,
            'description': instance.additional_costs,
        }
        Expense.objects.update_or_create(
            content_type=ContentType.objects.get_for_model(instance),
            object_id=instance.pk,
            defaults=expense_data
        )
    elif instance.additional_cost_amount == 0:
        # If additional_cost_amount is 0, delete any existing Expense record for this order
        Expense.objects.filter(content_type=ContentType.objects.get_for_model(instance), object_id=instance.pk).delete()
