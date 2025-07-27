import random
import string
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from django.core.management.base import BaseCommand
from apps.farm.models import Farmer

class Command(BaseCommand):
    help = 'Fixes duplicate email addresses in the Farmer model by randomizing part of the email.'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Starting to check for duplicate farmer email addresses...'))

        # Get all email addresses and count their occurrences
        email_addresses = Farmer.objects.values_list('email', flat=True).exclude(email__isnull=True).exclude(email__exact='').order_by('email')

        duplicate_emails = set()
        seen_emails = set()

        for email in email_addresses:
            if email in seen_emails:
                duplicate_emails.add(email)
            else:
                seen_emails.add(email)

        if not duplicate_emails:
            self.stdout.write(self.style.SUCCESS('No duplicate email addresses found. Exiting.'))
            return

        self.stdout.write(self.style.WARNING(f'Found {len(duplicate_emails)} duplicate email addresses. Attempting to fix...'))

        for dup_email in duplicate_emails:
            farmers_with_duplicate_email = Farmer.objects.filter(email=dup_email).order_by('id')

            # Keep the first one as is, modify the rest
            for farmer in farmers_with_duplicate_email[1:]:
                original_email = farmer.email
                if original_email:
                    try:
                        username, domain = original_email.split('@')
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f'Skipping farmer ID {farmer.id} as email "{original_email}" is not in a valid format.'))
                        continue

                    new_email_found = False
                    attempts = 0
                    max_attempts = 1000  # Prevent infinite loops

                    while not new_email_found and attempts < max_attempts:
                        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=5))
                        new_email = f'{username}_{random_suffix}@{domain}'

                        # Validate the new email format
                        try:
                            validate_email(new_email)
                        except ValidationError:
                            attempts += 1
                            continue

                        # Check if the new email already exists
                        if not Farmer.objects.filter(email=new_email).exists():
                            farmer.email = new_email
                            try:
                                farmer.save()
                                self.stdout.write(self.style.SUCCESS(f'Successfully updated farmer ID {farmer.id} from {original_email} to {new_email}'))
                                new_email_found = True
                            except IntegrityError:
                                # This can happen if another process creates the same email concurrently
                                self.stdout.write(self.style.WARNING(f'IntegrityError when saving farmer ID {farmer.id} with new email {new_email}. Retrying...'))
                                attempts += 1
                            except ValidationError as e:
                                self.stdout.write(self.style.ERROR(f'Validation error for farmer ID {farmer.id} with new email {new_email}: {e}. Retrying...'))
                                attempts += 1
                        else:
                            attempts += 1

                    if not new_email_found:
                        self.stdout.write(self.style.ERROR(f'Failed to find a unique email for farmer ID {farmer.id} (original: {original_email}) after {max_attempts} attempts.'))
                else:
                    self.stdout.write(self.style.WARNING(f'Skipping farmer ID {farmer.id} as email is empty.'))

        self.stdout.write(self.style.SUCCESS('Finished checking for duplicate farmer email addresses.'))
