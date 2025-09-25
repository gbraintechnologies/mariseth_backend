import requests
import csv
from io import StringIO
from django.core.management.base import BaseCommand
from apps.farm.models import Farmer
from apps.farm.utils import generate_farmer_id
from apps.organizations.models import Organization
from apps.shared.models import Region, District
from datetime import datetime


class Command(BaseCommand):
    help = 'Import lead farmers from a CSV file on S3, associating them with an organization.'

    def add_arguments(self, parser):
        parser.add_argument('url', type=str, help='The S3 URL of the CSV file to import.')
        parser.add_argument('--organization-id', type=int, required=True, help='The ID of the organization to associate farmers with.')

    def handle(self, *args, **options):
        url = options['url']
        organization_id = options['organization_id']

        try:
            organization = Organization.objects.get(pk=organization_id)
            self.stdout.write(self.style.SUCCESS(f'Using organization: {organization.name}'))
        except Organization.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Organization with ID {organization_id} not found."))
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
            'First Name', 'Other Names', 'Last Name', 'Phone Number', 'Gender', 'DOB',
            'Country', 'Region', 'District', 'Village/Community', 'ID_Type', 'ID_Number', 'Address', 'Farming Type'
        ]

        if not all(header in reader.fieldnames for header in required_headers):
            missing_headers = [header for header in required_headers if header not in reader.fieldnames]
            self.stderr.write(self.style.ERROR(f"CSV is missing one or more required headers: {', '.join(missing_headers)}"))
            return

        for row in reader:
            phone_number = row.get('Phone Number')
            if not phone_number:
                self.stdout.write(self.style.WARNING(f"Skipping row due to missing phone number."))
                continue

            if Farmer.objects.filter(phone_number=phone_number).exists():
                self.stdout.write(self.style.WARNING(f"Farmer with phone number {phone_number} already exists. Skipping."))
                continue

            try:
                region_id = row.get('Region')
                district_id = row.get('District')

                region = Region.objects.get(id=region_id) if region_id else None
                district = District.objects.get(id=district_id) if district_id else None

                dob = None
                if row.get('DOB'):
                    try:
                        dob = datetime.strptime(row.get('DOB'), '%m/%d/%Y').date()
                    except ValueError:
                        self.stdout.write(self.style.WARNING(f"Could not parse date '{row.get('DOB')}'. Setting to null."))

                farmer_id = generate_farmer_id(organization.id)
                farming_type = row.get('Farming Type')

                Farmer.objects.create(
                    organization=organization,
                    farmer_id=farmer_id,
                    first_name=row.get('First Name'),
                    last_name=row.get('Last Name'),
                    other_names=row.get('Other Names'),
                    phone_number=phone_number,
                    gender=row.get('Gender', '').lower(),
                    date_of_birth=dob,
                    country=row.get('Country'),
                    region=region,
                    district=district,
                    village=row.get('Village/Community'),
                    id_type=row.get('ID_Type'),
                    id_number=row.get('ID_Number'),
                    address=row.get('Address'),
                    type='lead',
                    leadership_experience=[farming_type] if farming_type else []
                )
                self.stdout.write(self.style.SUCCESS(f"Successfully created lead farmer: {row.get('First Name')} {row.get('Last Name')}"))

            except Region.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Region with name {region_id} not found. Skipping row."))
            except District.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"District with name {district_id} not found. Skipping row."))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"An error occurred: {e}"))

        self.stdout.write(self.style.SUCCESS("Lead farmer import process complete."))
