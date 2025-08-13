from django.core.management.base import BaseCommand
from django.db import transaction

from apps.inflow.models import InflowOrder, InflowOrderProduct


class Command(BaseCommand):
    help = 'Recalculates and updates total_cost, total_products_cost, and total_bags for InflowOrders with zero values.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to update InflowOrders...'))

        from django.db.models import Q
        orders_to_update = InflowOrder.objects.filter(
            Q(total_cost=0, total_products_cost=0) | Q(total_weight=0)
        )

        if not orders_to_update.exists():
            self.stdout.write(self.style.SUCCESS('No InflowOrders found with zero total_cost and total_products_cost.'))
            return

        updated_count = 0
        for order in orders_to_update:
            with transaction.atomic():
                total_products_costs = 0
                total_bags = 0
                total_weight = 0

                # Ensure products are fetched correctly
                products = InflowOrderProduct.objects.filter(order=order, is_active=True)

                for product in products:
                    # Recalculate product total_cost and total_weight if they are not already correct
                    product_fields_to_update = []
                    if product.total_cost != (product.unit_price * product.quantity):
                        product.total_cost = product.unit_price * product.quantity
                        product_fields_to_update.append('total_cost')
                    
                    # Assuming product.product.weight exists and is a DecimalField
                    expected_total_weight = product.product.weight * product.quantity
                    if product.total_weight != expected_total_weight:
                        product.total_weight = expected_total_weight
                        product_fields_to_update.append('total_weight')

                    if product_fields_to_update:
                        product.save(update_fields=product_fields_to_update)

                    total_products_costs += product.total_cost
                    total_bags += product.quantity
                    total_weight += product.total_weight

                order.total_products_cost = total_products_costs
                order.total_cost = total_products_costs + order.additional_cost_amount
                order.total_bags = total_bags
                order.total_weight = total_weight
                order.save(update_fields=['total_products_cost', 'total_cost', 'total_bags', 'total_weight'])
                updated_count += 1
                self.stdout.write(self.style.SUCCESS(f'Updated InflowOrder: {order.order_id}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} InflowOrders.'))
