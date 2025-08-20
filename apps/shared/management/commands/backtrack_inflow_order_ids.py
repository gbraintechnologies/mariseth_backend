
from django.core.management.base import BaseCommand
from apps.inflow.models import InflowOrder

class Command(BaseCommand):
    help = 'Backtrack inflow order IDs to the new format'

    def handle(self, *args, **options):
        orders = InflowOrder.objects.all()
        for order in orders:
            new_order_id = f"ORD-i{order.id}"
            if order.order_id != new_order_id:
                order.order_id = new_order_id
                order.save(update_fields=['order_id'])
                self.stdout.write(self.style.SUCCESS(f'Successfully updated order {order.id} to {new_order_id}'))
            else:
                self.stdout.write(self.style.WARNING(f'Order {order.id} already has the correct order_id'))
