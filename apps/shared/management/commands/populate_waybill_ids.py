from django.core.management.base import BaseCommand
from apps.inflow.models import InflowOrder
from apps.outflow.models import OutflowOrder
from apps.inflow.utils import generate_inflow_waybill_id
from apps.outflow.utils import generate_outflow_waybill_id

class Command(BaseCommand):
    help = 'Populates waybill IDs for existing InflowOrder and OutflowOrder objects.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting population of waybill IDs...'))

        # Populate InflowOrder waybill IDs
        inflow_orders = InflowOrder.objects.filter(waybill_id__isnull=True)
        self.stdout.write(self.style.SUCCESS(f'Processing {inflow_orders.count()} InflowOrders...'))
        for order in inflow_orders:
            order.waybill_id = generate_inflow_waybill_id(order.pk)
            order.save(update_fields=['waybill_id'])
            self.stdout.write(self.style.SUCCESS(f'Updated InflowOrder ID: {order.id} with Waybill ID: {order.waybill_id}'))

        # Populate OutflowOrder waybill IDs
        outflow_orders = OutflowOrder.objects.filter(waybill_id__isnull=True)
        self.stdout.write(self.style.SUCCESS(f'Processing {outflow_orders.count()} OutflowOrders...'))
        for order in outflow_orders:
            order.waybill_id = generate_outflow_waybill_id(order.pk)
            order.save(update_fields=['waybill_id'])
            self.stdout.write(self.style.SUCCESS(f'Updated OutflowOrder ID: {order.id} with Waybill ID: {order.waybill_id}'))

        self.stdout.write(self.style.SUCCESS('Waybill ID population complete.'))
