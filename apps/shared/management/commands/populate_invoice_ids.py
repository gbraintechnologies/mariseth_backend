from django.core.management.base import BaseCommand
from apps.outflow.models import OutflowOrderPayments
from apps.outflow.utils import generate_invoice_id


class Command(BaseCommand):
    help = 'Populates invoice_id for existing OutflowOrderPayments where it is null.'

    def handle(self, *args, **options):
        payments_to_update = OutflowOrderPayments.objects.filter(invoice_id__isnull=True)
        updated_count = 0

        self.stdout.write(f"Found {payments_to_update.count()} OutflowOrderPayments to update.")

        for payment in payments_to_update:
            payment.invoice_id = generate_invoice_id(payment.pk)
            payment.save()
            updated_count += 1

        self.stdout.write(self.style.SUCCESS(f"Successfully updated {updated_count} OutflowOrderPayments with invoice_id."))
