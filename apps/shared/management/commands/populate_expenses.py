from django.core.management.base import BaseCommand
from django.contrib.contenttypes.models import ContentType
from apps.inflow.models import InflowOrder
from apps.outflow.models import OutflowOrder
from apps.accounting.models import Expense

class Command(BaseCommand):
    help = 'Populates the Expense model from existing InflowOrder and OutflowOrder data.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting population of Expense model...'))

        # Populate from InflowOrder
        inflow_orders = InflowOrder.objects.all()
        self.stdout.write(self.style.SUCCESS(f'Processing {inflow_orders.count()} InflowOrders...'))
        for order in inflow_orders:
            if order.additional_cost_amount > 0:
                expense, created = Expense.objects.update_or_create(
                    content_type=ContentType.objects.get_for_model(order),
                    object_id=order.pk,
                    defaults={
                        'order_type': 'inflow',
                        'amount': order.additional_cost_amount,
                        'description': order.additional_costs,
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created Expense for InflowOrder ID: {order.id}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Updated Expense for InflowOrder ID: {order.id}'))
            else:
                self.stdout.write(self.style.WARNING(f'Skipping InflowOrder ID: {order.id} (additional_cost_amount is zero).'))

        # Populate from OutflowOrder
        outflow_orders = OutflowOrder.objects.all()
        self.stdout.write(self.style.SUCCESS(f'Processing {outflow_orders.count()} OutflowOrders...'))
        for order in outflow_orders:
            if order.additional_cost_amount > 0:
                expense, created = Expense.objects.update_or_create(
                    content_type=ContentType.objects.get_for_model(order),
                    object_id=order.pk,
                    defaults={
                        'order_type': 'outflow',
                        'amount': order.additional_cost_amount,
                        'description': order.additional_costs,
                    }
                )
                if created:
                    self.stdout.write(self.style.SUCCESS(f'Created Expense for OutflowOrder ID: {order.id}'))
                else:
                    self.stdout.write(self.style.SUCCESS(f'Updated Expense for OutflowOrder ID: {order.id}'))
            else:
                self.stdout.write(self.style.WARNING(f'Skipping OutflowOrder ID: {order.id} (additional_cost_amount is zero).'))

        self.stdout.write(self.style.SUCCESS('Expense model population complete.'))