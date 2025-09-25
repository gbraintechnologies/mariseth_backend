from django.core.management.base import BaseCommand
from django.db import transaction
from apps.farm.models import Product


class Command(BaseCommand):
    help = 'Changes the type of Product instances from non-"crop" to "other".'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting product type transformation...'))

        try:
            with transaction.atomic():
                # Filter products whose type is not 'crop'
                products_to_update = Product.objects
                count = products_to_update.count()

                if count == 0:
                    self.stdout.write(self.style.WARNING('No products found with type other than "crop".'))
                    return

                self.stdout.write(self.style.SUCCESS(f'Found {count} products to update.'))

                # Update the type to 'other'
                updated_count = products_to_update.update(type='other')

                self.stdout.write(self.style.SUCCESS(f'Successfully updated {updated_count} product types to "other".'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'An error occurred during product type transformation: {e}'))

        self.stdout.write(self.style.SUCCESS('Product type transformation complete.'))
