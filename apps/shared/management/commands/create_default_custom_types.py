from django.core.management.base import BaseCommand
from django.db import transaction

from apps.shared.models import CustomType


class Command(BaseCommand):
    help = 'Create default CustomType instances for Mr., Mrs., and Miss.'

    def handle(self, *args, **kwargs):
        default_types = [
            {'name': 'Mr.', 'category_name': 'title', 'category_type': 'title', 'is_default': True},
            {'name': 'Mrs.', 'category_name': 'title', 'category_type': 'title', 'is_default': True},
            {'name': 'Miss', 'category_name': 'title', 'category_type': 'title', 'is_default': True},
            {'name': "no-reply@mariseth360.com", 'category_name': 'default_email', 'category_type': 'default_email',
             'is_default': True, 'is_hidden': True},
            {'name': "staging.mariseth360.com", 'category_name': 'default_domain',
             'category_type': 'default_domain',
             'is_default': True, 'is_hidden': True}
        ]

        with transaction.atomic():
            for data in default_types:
                try:
                    custom_type, created = CustomType.objects.get_or_create(
                        name=data['name'],
                        category_name=data['category_name'],
                        defaults={
                            'category_type': data['category_type'],
                            'is_default': data['is_default'],
                            'is_hidden': data.get('is_hidden', False)
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Successfully created CustomType "{custom_type.name}"'))
                    else:
                        self.stdout.write(self.style.WARNING(f'CustomType "{custom_type.name}" already exists'))
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f'Error creating CustomType: {e}'))
