import random

from django.core.management.base import BaseCommand
from django.db.models import Count

from apps.farm.models import Farmer


class Command(BaseCommand):
    help = 'Fix duplicate farmer phone numbers by replacing the last 3 digits with random digits'

    def handle(self, *args, **kwargs):
        duplicates = (
            Farmer.objects
            .exclude(phone_number__isnull=True)
            .exclude(phone_number='')
            .values('phone_number')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )

        total_fixed = 0

        for entry in duplicates:
            phone = entry['phone_number']
            farmers_with_same_phone = Farmer.objects.filter(phone_number=phone).order_by('id')

            # Keep the first one unchanged, modify the rest
            for farmer in farmers_with_same_phone[1:]:
                original_number = farmer.phone_number or ''
                if len(original_number) < 3:
                    self.stdout.write(self.style.WARNING(
                        f"Skipping Farmer {farmer.id} with short number: {original_number}"
                    ))
                    continue

                # Replace last 3 digits with random ones
                new_suffix = ''.join([str(random.randint(0, 9)) for _ in range(3)])
                new_number = original_number[:-3] + new_suffix

                # Ensure uniqueness just in case
                while Farmer.objects.filter(phone_number=new_number).exists():
                    new_suffix = ''.join([str(random.randint(0, 9)) for _ in range(3)])
                    new_number = original_number[:-3] + new_suffix

                self.stdout.write(self.style.SUCCESS(
                    f"Fixing Farmer ID {farmer.id} | {original_number} → {new_number}"
                ))

                farmer.phone_number = new_number
                farmer.save()
                total_fixed += 1

        self.stdout.write(self.style.SUCCESS(f"✅ Done. Total fixed: {total_fixed}"))
