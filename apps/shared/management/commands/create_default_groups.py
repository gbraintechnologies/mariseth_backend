from django.core.management.base import BaseCommand

from apps.accounts.models import AppGroup


class Command(BaseCommand):
    help = 'Create default groups and set their ranks'

    def handle(self, *args, **kwargs):
        # List of group names and ranks to get or create
        group_data = [{'name': 'Super Admin', 'rank': 1}]

        for data in group_data:
            group, created = AppGroup.objects.get_or_create(name=data['name'], is_default=True, rank=data['rank'])
            if created:
                self.stdout.write(self.style.SUCCESS(f'Successfully created group {data["name"]}'))
            else:
                self.stdout.write(self.style.WARNING(f'Group {data["name"]} already exists'))