
import requests
import csv
from io import StringIO
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.farm.models import Farmer


class Command(BaseCommand):
    help = 'Update farmer genders from a CSV file using their phone numbers.'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='The URL of the CSV file to import.')

    def handle(self, *args, **options):
        url = options['url']

        self.stdout.write(f"Downloading CSV from {url}")
        try:
            response = requests.get(url)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"Failed to download file: {e}"))
            return

        self.stdout.write("Processing CSV data...")
        csv_data = StringIO(response.text)
        reader = csv.DictReader(csv_data)

        required_headers = ['MSISDN', 'Value']
        if not all(header in reader.fieldnames for header in required_headers):
            self.stderr.write(self.style.ERROR(f"CSV is missing one or more required headers: {required_headers}. Found headers: {reader.fieldnames}"))
            return

        updated_count = 0
        not_found_count = 0
        skipped_count = 0

        for row in reader:
            phone_number = row.get('MSISDN')
            gender_value = row.get('Value', '').lower()

            if not phone_number:
                self.stdout.write(self.style.WARNING("Skipping row due to missing phone number (MSISDN)."))
                skipped_count += 1
                continue

            if gender_value not in ['m', 'f']:
                self.stdout.write(self.style.WARNING(f"Invalid gender value '{row.get('Value')}' for phone {phone_number}. Skipping."))
                skipped_count += 1
                continue

            try:
                with transaction.atomic():
                    try:
                        farmer = Farmer.objects.get(phone_number=phone_number)
                        if farmer.gender != gender_value:
                            farmer.gender = gender_value
                            farmer.save(update_fields=['gender'])
                            self.stdout.write(self.style.SUCCESS(f"Updated gender for farmer with phone number {phone_number} to '{gender_value}'."))
                            updated_count += 1
                        else:
                            self.stdout.write(self.style.NOTICE(f"Gender for farmer with phone number {phone_number} is already correct ('{farmer.gender}'). Skipping."))

                    except Farmer.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Farmer with phone number {phone_number} not found."))
                        not_found_count += 1

            except Exception as e:
                self.stderr.write(self.style.ERROR(f"An error occurred for phone number {phone_number}: {e}"))

        self.stdout.write(self.style.SUCCESS("\nGender update process complete."))
        self.stdout.write(self.style.SUCCESS(f"Successfully updated: {updated_count} farmers."))
        self.stdout.write(self.style.WARNING(f"Farmers not found: {not_found_count}."))
        self.stdout.write(self.style.NOTICE(f"Rows skipped (missing data or invalid gender): {skipped_count}."))
