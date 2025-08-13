from django.core.management.base import BaseCommand
from django.db import transaction

from apps.inflow.models import InflowOrder, InflowOrderProduct


class Command(BaseCommand):
    help = 'Recalculates and updates total_cost, total_products_cost, and total_bags for InflowOrders with zero values.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to update InflowOrders...'))

        orders_to_update = InflowOrder.objects.filter(
            total_cost=0,
            total_products_cost=0
        )

        if not orders_to_update.exists():
            self.stdout.write(self.style.SUCCESS('No InflowOrders found with zero total_cost and total_products_cost.'))
            return

        updated_count = 0
        for order in orders_to_update:
            with transaction.atomic():
                total_products_costs = 0
                total_bags = 0

                # Ensure products are fetched correctly
                products = InflowOrderProduct.objects.filter(order=order, is_active=True)

                for product in products:
                    # Recalculate product total_cost if it's not already correct
                    if product.total_cost != (product.unit_price * product.quantity):
                        product.total_cost = product.unit_price * product.quantity
                        product.save(update_fields=['total_cost'])

                    total_products_costs += product.total_cost
                    total_bags += product.quantity

                order.total_products_cost = total_products_costs
                order.total_cost = total_products_costs + order.additional_cost_amount
                order.total_bags = total_bags
                order.save(update_fields=['total_products_cost', 'total_cost', 'total_bags'])
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'Updated InflowOrder: {order.order_id}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} InflowOrders.'))
