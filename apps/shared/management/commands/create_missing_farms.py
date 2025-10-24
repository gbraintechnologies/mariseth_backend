import csv
import sys
import os
import requests
from io import StringIO
from datetime import datetime
from django.core.management.base import BaseCommand
from django.db import transaction

# Import necessary models
from apps.farm.models import Farm, Farmer
from apps.farm.utils import generate_farm_id
from apps.organizations.models import Organization

class Command(BaseCommand):
    help = 'Creates farms from a CSV if they do not already exist by name.'

    def add_arguments(self, parser):
        parser.add_argument('csv_location', type=str, help='The path or URL of the CSV file.')
        parser.add_argument('farm_name_column', type=str, help='The name of the column containing farm names.')
        parser.add_argument('--organization-id', type=int, required=True, help='The ID of the organization.')
        parser.add_argument('--farmer-id', type=int, required=True, help='The ID of the farmer to associate with new farms.')

    def handle(self, *args, **options):
        csv_location = options['csv_location']
        farm_name_column = options['farm_name_column']
        organization_id = options['organization_id']
        farmer_pk = options['farmer_id'] # Renamed to avoid confusion with farmer_id string

        self.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] Starting script to create missing farms...")

        try:
            organization = Organization.objects.get(pk=organization_id)
            self.stdout.write(self.style.SUCCESS(f'[{datetime.now().strftime('%H:%M:%S')}] Using organization: {organization.name}'))
        except Organization.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"[{datetime.now().strftime('%H:%M:%S')}] Organization with ID {organization_id} not found."))
            return

        try:
            farmer = Farmer.objects.get(pk=farmer_pk)
            self.stdout.write(self.style.SUCCESS(f'[{datetime.now().strftime('%H:%M:%S')}] Using farmer: {farmer.first_name} {farmer.last_name} (ID: {farmer.id})'))
        except Farmer.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"[{datetime.now().strftime('%H:%M:%S')}] Farmer with ID {farmer_pk} not found."))
            return

        self.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] Attempting to read CSV from {csv_location}...")
        lines = []
        fieldnames = []
        try:
            if csv_location.startswith('http://') or csv_location.startswith('https://'):
                response = requests.get(csv_location)
                response.raise_for_status()
                csv_data = StringIO(response.text)
                reader = csv.DictReader(csv_data)
                fieldnames = reader.fieldnames
                lines = list(reader)
            else:
                with open(csv_location, 'r', newline='', encoding='utf-8') as infile:
                    reader = csv.DictReader(infile)
                    fieldnames = reader.fieldnames
                    lines = list(reader)
            self.stdout.write(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully read CSV. Total rows: {len(lines)}")
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"[{datetime.now().strftime('%H:%M:%S')}] Error: File not found at '{csv_location}'"))
            return
        except requests.exceptions.RequestException as e:
            self.stderr.write(self.style.ERROR(f"[{datetime.now().strftime('%H:%M:%S')}] Error downloading file: {e}"))
            return
        except Exception as e:
            self.stderr.write(self.style.ERROR(f"[{datetime.now().strftime('%H:%M:%S')}] An error occurred while reading the CSV: {e}"))
            return

        if not fieldnames or farm_name_column not in fieldnames:
            self.stderr.write(self.style.ERROR(f"[{datetime.now().strftime('%H:%M:%S')}] Error: Column '{farm_name_column}' not found in the CSV file."))
            self.stderr.write(self.style.ERROR(f"[{datetime.now().strftime('%H:%M:%S')}] Available columns: {fieldnames}"))
            return

        # Add 'Land Size' to required headers for validation
        required_csv_headers = [farm_name_column, 'Land Size']
        if not all(header in fieldnames for header in required_csv_headers):
            self.stderr.write(self.style.ERROR(f"[{datetime.now().strftime('%H:%M:%S')}] Error: Missing one or more required CSV headers. Required: {required_csv_headers}, Found: {fieldnames}"))
            return

        created_count = 0
        skipped_count = 0

        for row in lines:
            farm_name = row.get(farm_name_column)
            if not farm_name:
                self.stdout.write(self.style.WARNING(f"[{datetime.now().strftime('%H:%M:%S')}] Skipping row due to missing farm name in column '{farm_name_column}'."))
                continue

            try:
                with transaction.atomic():
                    if Farm.objects.filter(name=farm_name, organization=organization).exists():
                        self.stdout.write(self.style.WARNING(f"[{datetime.now().strftime('%H:%M:%S')}] Farm '{farm_name}' already exists. Skipping creation."))
                        skipped_count += 1
                    else:
                        farm_id = generate_farm_id(organization.id)
                        
                        # Get land_size from CSV
                        land_size_str = row.get('Land Size')
                        land_size = None
                        if land_size_str:
                            try:
                                land_size = float(land_size_str) # Convert to float first, then Decimal if needed by model
                            except ValueError:
                                self.stdout.write(self.style.WARNING(f"[{datetime.now().strftime('%H:%M:%S')}] Invalid 'Land Size' value '{land_size_str}' for farm '{farm_name}'. Setting to None."))

                        Farm.objects.create(
                            organization=organization,
                            farmer=farmer,
                            farm_id=farm_id,
                            name=farm_name,
                            size=land_size, # Assign the size here
                            farm_type='external', # Defaulting to external
                            type='crop' # Defaulting to crop, as it's common
                        )
                        self.stdout.write(self.style.SUCCESS(f"[{datetime.now().strftime('%H:%M:%S')}] Successfully created farm: '{farm_name}'"))
                        created_count += 1
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"[{datetime.now().strftime('%H:%M:%S')}] An error occurred while processing farm '{farm_name}': {e}"))

        self.stdout.write(self.style.SUCCESS(f"[{datetime.now().strftime('%H:%M:%S')}] Script finished. Created {created_count} new farms, skipped {skipped_count} existing farms."))
