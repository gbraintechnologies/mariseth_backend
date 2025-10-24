import requests
import csv
from io import StringIO
from types import SimpleNamespace
from django.core.management.base import BaseCommand
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.farm.models import Farmer, Product
from apps.farm.serializers.farm import FarmSerializer
from apps.organizations.models import Organization
from apps.shared.models import Region, District, CustomType


class Command(BaseCommand):
    help = 'Import external farms from a CSV file using FarmSerializer.'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='The S3 URL of the CSV file to import.')
        parser.add_argument('--organization-id', type=int, required=True, help='The ID of the organization.')
        parser.add_argument('--user-id', type=int, required=True, help='The ID of the user performing the import.')

    def handle(self, *args, **options):
        url = options['url']
        organization_id = options['organization_id']
        user_id = options['user_id']

        try:
            organization = Organization.objects.get(pk=organization_id)
            self.stdout.write(self.style.SUCCESS(f'Using organization: {organization.name}'))
        except Organization.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Organization with ID {organization_id} not found."))
            return

        try:
            user = User.objects.get(pk=user_id)
            self.stdout.write(self.style.SUCCESS(f'Running as user: {user.email}'))
        except User.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"User with ID {user_id} not found."))
            return

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

        required_headers = [
            'Farm Name', 'Farm Location (Town)', 'Region', 'District', 'Lead Farmer ID',
            'Land Size', 'Metrix', 'Onwership Type', 'Crop', 'Irrigation', 'Access to Market'
        ]

        if not all(header in reader.fieldnames for header in required_headers):
            self.stderr.write(self.style.ERROR(f"CSV is missing one or more required headers. Required: {required_headers}, Found: {reader.fieldnames}"))
            return

        mock_request = SimpleNamespace(user=user, organization=organization)

        for row in reader:
            farm_name = row.get('Farm Name')
            if not farm_name:
                self.stdout.write(self.style.WARNING("Skipping row due to missing 'Farm Name'."))
                continue

            try:
                with transaction.atomic():
                    # --- Prepare data for the serializer ---
                    farm_data = {'name': farm_name}

                    # Get Farmer ID (PK)
                    farmer_id_str = row.get('Lead Farmer ID')
                    if not farmer_id_str:
                        self.stdout.write(self.style.WARNING(f"Skipping farm '{farm_name}' due to missing 'Lead Farmer ID'."))
                        continue
                    try:
                        farmer = Farmer.objects.get(farmer_id=farmer_id_str, organization=organization)
                        farm_data['farmer'] = farmer.id
                    except Farmer.DoesNotExist:
                        self.stderr.write(self.style.ERROR(f"Farmer with farmer_id '{farmer_id_str}' not found. Skipping farm '{farm_name}'."))
                        continue

                    # Get Region and District IDs
                    if row.get('Region'):
                        farm_data['region'] = int(row.get('Region'))
                    if row.get('District'):
                        farm_data['district'] = int(row.get('District'))

                    # Get Metric ID
                    if row.get('Metrix'):
                        try:
                            metric = CustomType.objects.get(name__icontains=row.get('Metrix'), organization=organization, category_name='size_metric')
                            farm_data['size_metric'] = metric.id
                        except CustomType.DoesNotExist:
                            self.stderr.write(self.style.ERROR(f"Metric '{row.get('Metrix')}' not found. Skipping farm '{farm_name}'."))
                            continue
                    
                    # Get Crop Product ID
                    if row.get('Crop'):
                        try:
                            # Assuming crop name is unique for type 'crop' in the organization
                            product = Product.objects.get(product_id__iexact=row.get('Crop'), organization=organization)
                            farm_data['crops'] = [product.id]
                        except Product.DoesNotExist:
                            self.stderr.write(self.style.ERROR(f"Crop Product '{row.get('Crop')}' not found. Skipping farm '{farm_name}'."))
                            continue
                        except Product.MultipleObjectsReturned:
                            self.stderr.write(self.style.ERROR(f"Multiple Crop Products found for '{row.get('Crop')}'. Skipping farm '{farm_name}'."))
                            continue

                    farm_data['location'] = row.get('Farm Location (Town)')
                    farm_data['size'] = row.get('Land Size') if row.get('Land Size') else None
                    farm_data['land_ownership'] = row.get('Onwership Type', '').lower()
                    farm_data['irrigation'] = row.get('Irrigation', '').lower() == 'yes'
                    farm_data['has_access_to_market'] = row.get('Access to Market', '').lower() == 'yes'
                    
                    # Set defaults for fields not in CSV
                    farm_data['farm_type'] = 'external' # Defaulting to 'crop' as it's the most common

                    # --- Use Serializer to Create Farm ---
                    serializer = FarmSerializer(data=farm_data, context={'request': mock_request})
                    
                    if serializer.is_valid(raise_exception=False):
                        serializer.save()
                        self.stdout.write(self.style.SUCCESS(f"Successfully created farm: {farm_name}"))
                    else:
                        self.stderr.write(self.style.ERROR(f"Validation error for farm '{farm_name}': {serializer.errors}"))

            except (ValidationError, Exception) as e:
                self.stderr.write(self.style.ERROR(f"An error occurred processing farm '{farm_name}': {e}"))

        self.stdout.write(self.style.SUCCESS("External farm import process complete."))
