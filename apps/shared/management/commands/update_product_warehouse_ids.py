from django.core.management.base import BaseCommand
from django.db import transaction

from apps.farm.models import Product
from apps.farm.utils import generate_product_id
from apps.warehouse.models import Warehouse
from apps.warehouse.utils import generate_warehouse_id


class Command(BaseCommand):
    help = 'Updates product_id for Product models and warehouse_id for Warehouse models using their respective name fields.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting ID update for Product and Warehouse models...'))

        # Update Product IDs
        self.stdout.write(self.style.SUCCESS('Updating Product IDs...'))
        products_updated = 0
        with transaction.atomic():
            for product in Product.objects.all():
                try:
                    new_product_id = generate_product_id(product.name)
                    if product.product_id != new_product_id:
                        product.product_id = new_product_id
                        product.save(update_fields=['product_id'])
                        products_updated += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'Updated Product ID for {product.name} (ID: {product.id}) to {new_product_id}'))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'Product ID for {product.name} (ID: {product.id}) is already up to date.'))
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error updating Product ID for {product.name} (ID: {product.id}): {e}'))
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {products_updated} Product IDs.'))

        # Update Warehouse IDs
        self.stdout.write(self.style.SUCCESS('Updating Warehouse IDs...'))
        warehouses_updated = 0
        with transaction.atomic():
            for warehouse in Warehouse.objects.all():
                try:
                    new_warehouse_id = generate_warehouse_id(warehouse.name)
                    if warehouse.warehouse_id != new_warehouse_id:
                        warehouse.warehouse_id = new_warehouse_id
                        warehouse.save(update_fields=['warehouse_id'])
                        warehouses_updated += 1
                        self.stdout.write(self.style.SUCCESS(
                            f'Updated Warehouse ID for {warehouse.name} (ID: {warehouse.id}) to {new_warehouse_id}'))
                    else:
                        self.stdout.write(self.style.WARNING(
                            f'Warehouse ID for {warehouse.name} (ID: {warehouse.id}) is already up to date.'))
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error updating Warehouse ID for {warehouse.name} (ID: {warehouse.id}): {e}'))
        self.stdout.write(self.style.SUCCESS(f'Successfully updated {warehouses_updated} Warehouse IDs.'))

        self.stdout.write(self.style.SUCCESS('ID update process complete.'))
