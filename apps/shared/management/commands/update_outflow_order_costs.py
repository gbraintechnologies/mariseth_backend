from django.core.management.base import BaseCommand
from django.db import transaction
from django.db.models import Q

from apps.outflow.models import OutflowOrder, OutflowOrderWarehouse, OutflowOrderWarehouseProduct


class Command(BaseCommand):
    help = 'Recalculates and updates total_cost, total_quantity, and total_weight for OutflowOrders, OutflowOrderWarehouses, and OutflowOrderWarehouseProducts with zero or incorrect values.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to update OutflowOrders...'))

        # Filter for OutflowOrders that need updating
        orders_to_update = OutflowOrder.objects.filter(
            Q(total_cost=0) | Q(total_quantity=0) | Q(total_weight=0) |
            Q(warehouses__total_quantity=0) | Q(warehouses__total_cost=0) | Q(warehouses__total_weight=0) |
            Q(warehouses__products__expected_quantity=0) | Q(warehouses__products__cost=0) | Q(warehouses__products__total_weight=0)
        ).distinct()

        if not orders_to_update.exists():
            self.stdout.write(self.style.SUCCESS('No OutflowOrders found with zero total_cost, total_quantity, or total_weight.'))
            return

        updated_order_count = 0
        for order in orders_to_update:
            with transaction.atomic():
                order_total_quantity = 0
                order_total_cost = 0
                order_total_weight = 0

                warehouses_to_update = order.warehouses.all()
                for warehouse in warehouses_to_update:
                    warehouse_total_quantity = 0
                    warehouse_total_cost = 0
                    warehouse_total_weight = 0

                    products_to_update = warehouse.products.all()
                    for product_line in products_to_update:
                        # Recalculate product_line.cost and product_line.total_weight
                        product_line_fields_to_update = []

                        expected_cost = product_line.expected_quantity * product_line.price_per_unit
                        if product_line.cost != expected_cost:
                            product_line.cost = expected_cost
                            product_line_fields_to_update.append('cost')
                        
                        # Assuming product_line.product.weight exists and is a DecimalField
                        expected_total_weight = product_line.product.weight * product_line.expected_quantity
                        if product_line.total_weight != expected_total_weight:
                            product_line.total_weight = expected_total_weight
                            product_line_fields_to_update.append('total_weight')

                        if product_line_fields_to_update:
                            product_line.save(update_fields=product_line_fields_to_update)

                        warehouse_total_quantity += product_line.expected_quantity
                        warehouse_total_cost += product_line.cost
                        warehouse_total_weight += product_line.total_weight

                    # Update OutflowOrderWarehouse totals
                    warehouse_fields_to_update = []
                    if warehouse.total_quantity != warehouse_total_quantity:
                        warehouse.total_quantity = warehouse_total_quantity
                        warehouse_fields_to_update.append('total_quantity')
                    if warehouse.total_cost != warehouse_total_cost:
                        warehouse.total_cost = warehouse_total_cost
                        warehouse_fields_to_update.append('total_cost')
                    if warehouse.total_weight != warehouse_total_weight:
                        warehouse.total_weight = warehouse_total_weight
                        warehouse_fields_to_update.append('total_weight')
                    
                    if warehouse_fields_to_update:
                        warehouse.save(update_fields=warehouse_fields_to_update)

                    order_total_quantity += warehouse.total_quantity
                    order_total_cost += warehouse.total_cost
                    order_total_weight += warehouse.total_weight

                # Update OutflowOrder totals
                order_fields_to_update = []
                if order.total_quantity != order_total_quantity:
                    order.total_quantity = order_total_quantity
                    order_fields_to_update.append('total_quantity')
                if order.total_cost != order_total_cost:
                    order.total_cost = order_total_cost + order.additional_cost_amount # Add additional_cost_amount
                    order_fields_to_update.append('total_cost')
                if order.total_weight != order_total_weight:
                    order.total_weight = order_total_weight
                    order_fields_to_update.append('total_weight')
                
                if order_fields_to_update:
                    order.save(update_fields=order_fields_to_update)
                
                updated_order_count += 1
                self.stdout.write(self.style.SUCCESS(f'Updated OutflowOrder: {order.order_id}'))

        self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_order_count} OutflowOrders.'))
