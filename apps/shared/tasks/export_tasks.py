from datetime import datetime
from io import BytesIO, StringIO

import pandas as pd
import sentry_sdk
from celery import shared_task
from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.credit.models import Credit
from apps.credit.serializers.credits import CreditExportSerializer
from apps.farm.models import Farm, Farmer, Product
from apps.farm.serializers.farm import FarmExportSerializer
from apps.farm.serializers.farmer import FarmerExportSerializer
from apps.farm.serializers.products import ProductExportSerializer
from apps.farm.utils import build_farm_filter_q, build_farmer_filter_q, build_product_filter_q
from apps.organizations.models import Organization
from apps.shared.consumers.notifications import send_client_notification
from apps.shared.utils.s3_upload import upload_to_s3
from apps.warehouse.models import Warehouse
from apps.warehouse.serializers import WarehouseExportSerializer
from mariseth.logging import logger

User = get_user_model()


@shared_task
def process_farm_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params['user_id'])
        organization = Organization.objects.get(pk=filter_params['organization_id'])
        farm_type = filter_params['farm_type']
        filter_q = build_farm_filter_q(filter_params, organization)
        farms = (
            Farm.objects.select_related('created_by').prefetch_related('farmproduct_set', 'farmers')
            .filter(filter_q).order_by("-date_created").distinct()
        )
        serializer = FarmExportSerializer(farms, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        # Base column mapping
        column_map = {
            'farm_id': 'Farm ID',
            'farm_type': 'Farm Type',
            'name': 'Farm Name',
            'location': 'Location',
            'region': 'Region',
            'district': 'District',
            'size': 'Size',
            'size_metric': 'Size Unit',
            'land_ownership': 'Land Ownership',
            'other_specification': 'Ownership Details',
            'farmer': 'Farmer',
            'created_by': 'Created By',
            'date_created': 'Date Created'
        }

        # Type-specific columns
        if farm_type == 'internal':
            column_map.update({
                'irrigation': 'Has Irrigation',
                'use_of_fertilizers': 'Fertilizer Use',
                'farming_methods': 'Farming Methods',
                'provide_training': 'Provides Training',
                'government_ngo_support': 'Receives Support',
                'specify_support': 'Support Details',
                'areas_of_assistance': 'Assistance Areas'
            })
        elif farm_type == 'external':
            column_map.update({
                'livestock_kept': 'Livestock',
                'has_access_to_market': 'Market Access',
                'type': 'Farm Specialty'
            })

        df.rename(columns=column_map, inplace=True)

        # Conditionally format columns based on farm type
        if farm_type == 'internal':
            # Process JSON fields
            df['Fertilizer Use'] = df['Fertilizer Use'].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else ""
            )
            df['Farming Methods'] = df['Farming Methods'].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else ""
            )
            # Convert boolean to Yes/No
            df['Has Irrigation'] = df['Has Irrigation'].map({True: 'Yes', False: 'No'})
            df['Provides Training'] = df['Provides Training'].map({True: 'Yes', False: 'No'})
            df['Receives Support'] = df['Receives Support'].map({True: 'Yes', False: 'No'})
        elif farm_type == 'external':
            # Process livestock data
            df['Livestock'] = df['Livestock'].apply(
                lambda x: x if isinstance(x, str) else ""
            )
            df['Market Access'] = df['Market Access'].map({True: 'Yes', False: 'No'})

        file_name = f"Farms_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode('utf-8'))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return
        group_names = [
            f'user_{user.id}'
        ]
        message = {
            "has_permission": True,
            "results": s3_url,
        }
        send_client_notification(
            message=message,
            message_type="export_notification",
            group_names=group_names
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Farm export failed: {str(e)}")

@shared_task
def process_product_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params['user_id'])
        organization = Organization.objects.get(pk=filter_params['organization_id'])

        filter_q = build_product_filter_q(filter_params, organization)
        product_type = filter_params['type']

        products = Product.objects.select_related(
            'category', 'weight_metric', 'quantity_metric', 'created_by'
        ).filter(filter_q).order_by("-date_created").distinct()

        serializer = ProductExportSerializer(products, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        column_map = {
            'product_id': 'Product ID',
            'name': 'Name',
            'type': 'Type',
            'category': 'Category',
            'weight': 'Weight',
            'weight_metric': 'Weight Unit',
            'quantity': 'Quantity',
            'quantity_metric': 'Quantity Unit',
            'season_status': 'Season Status',
            'status': 'Status',
            'season_start': 'Season Start',
            'season_end': 'Season End',
            'description': 'Description',
            'breed': 'Breed',
            'created_by': 'Created By',
            'date_created': 'Date Created',
            'last_updated': 'Last Updated'
        }

        df.rename(columns=column_map, inplace=True)

        if product_type == 'livestock':
            df['Weight'] = df['Weight'].apply(lambda x: f"{x} kg" if pd.notnull(x) else "")
            df.drop(['Season Start', 'Season End', 'Quantity Unit'], axis=1, inplace=True)
        elif product_type == 'crops':
            df['Quantity'] = df['Quantity'].apply(lambda x: f"{x} bags" if pd.notnull(x) else "")
            df.drop(['Breed', 'Weight', 'Weight Unit'], axis=1, inplace=True)

        file_name = f"Products_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode('utf-8'))

        s3_url = upload_to_s3(file_data, file_name)
        if not s3_url:
            return
        group_names = [
            f'user_{user.id}'
        ]
        message = {
            "has_permission": True,
            "results": s3_url,
        }
        send_client_notification(
            message=message,
            message_type="export_notification",
            group_names=group_names
        )
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Product export failed: {str(e)}")


@shared_task
def process_farmer_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params['user_id'])
        organization = Organization.objects.get(pk=filter_params['organization_id'])

        filter_q = build_farmer_filter_q(filter_params, organization)

        farmers = (
            Farmer.objects.select_related('farm', 'lead_farmer', 'created_by', 'region', 'district')
            .filter(filter_q).order_by('-date_created').distinct()
        )

        serializer = FarmerExportSerializer(farmers, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        # Base column mapping
        column_map = {
            'farmer_id': 'Farmer ID',
            'type': 'Type',
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'other_names': 'Other Names',
            'gender': 'Gender',
            'date_of_birth': 'Date of Birth',
            'id_type': 'ID Type',
            'id_number': 'ID Number',
            'phone_number': 'Phone Number',
            'email': 'Email',
            'address': 'Address',
            'village': 'Village',
            'region': 'Region',
            'district': 'District',
            'country': 'Country',
            'farm': 'Farm',
            'lead_farmer': 'Lead Farmer',
            'created_by': 'Created By',
            'date_created': 'Date Created'
        }

        df.rename(columns=column_map, inplace=True)

        file_name = f"Farmers_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode('utf-8'))

        s3_url = upload_to_s3(file_data, file_name)
        if not s3_url:
            return

        group_names = [
            f'user_{user.id}'
        ]
        message = {
            "has_permission": True,
            "results": s3_url,
        }
        send_client_notification(
            message=message,
            message_type="export_notification",
            group_names=group_names
        )
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Farmer export failed: {str(e)}")


@shared_task
def process_credit_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params['user_id'])
        organization = Organization.objects.get(pk=filter_params['organization_id'])
        query = filter_params.get('query')
        payment_status = filter_params.get('payment_status')
        input_type = filter_params.get('input_type')
        date_from = filter_params.get('date_from')
        date_to = filter_params.get('date_to')
        filter_q = Q(is_active=True, organization=organization)
        if query:
            filter_q &= (
                    Q(id__icontains=query) |
                    Q(farmer__first_name__icontains=query) |
                    Q(farmer__last_name__icontains=query)
            )
        if payment_status:
            filter_q &= Q(payment_status=payment_status.lower())
        if input_type:
            filter_q &= Q(type=input_type.lower())
        if date_from and date_to:
            filter_q &= Q(issue_date__range=[date_from, date_to])
        credits = Credit.objects.select_related('farmer').filter(filter_q).order_by('-issue_date')
        serializer = CreditExportSerializer(credits, many=True)
        df = pd.DataFrame(serializer.data)
        column_map = {
            'id': 'Credit ID',
            'farmer': 'Farmer',
            'type': 'Credit Type',
            'quantity': 'Quantity',
            'credit_amount': 'Credit Amount',
            'issue_date': 'Issue Date',
            'due_date': 'Due Date',
            'interest_rate': 'Interest Rate (%)',
            'outstanding_amount': 'Outstanding Amount',
            'payment_status': 'Payment Status',
            'approval_status': 'Approval Status',
            'main_crops': 'Main Crops',
            'created_by': 'Created By',
            'date_created': 'Creation Date'
        }
        df.rename(columns=column_map, inplace=True)
        file_name = f"Credits_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode('utf-8'))

        s3_url = upload_to_s3(file_data, file_name)
        if not s3_url:
            return
        group_names = [f'user_{user.id}']
        message = {
            "has_permission": True,
            "results": s3_url,
            "export_type": "export_credits"
        }
        send_client_notification(
            message=message,
            message_type="export_notification",
            group_names=group_names
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Credit export failed: {str(e)}")


@shared_task
def process_warehouse_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params['user_id'])
        organization = Organization.objects.get(pk=filter_params['organization_id'])

        # Extract filters
        query = filter_params.get('query')
        region = filter_params.get('region')
        district = filter_params.get('district')
        date_from = filter_params.get('date_from')
        date_to = filter_params.get('date_to')

        filter_q = Q(is_active=True, organization=organization)

        if region:
            filter_q &= Q(region=region)
        if district:
            filter_q &= Q(district=district)
        if date_from and date_to:
            filter_q &= Q(date_created__date__range=[date_from, date_to])
        if query:
            filter_q &= (
                Q(name__icontains=query) |
                Q(warehouse_id__icontains=query) |
                Q(description__icontains=query)
            )

        warehouses = Warehouse.objects.select_related(
            'manager', 'organization'
        ).filter(filter_q).order_by("-date_created")

        serializer = WarehouseExportSerializer(warehouses, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)
        column_map = {
            'warehouse_id': 'Warehouse ID',
            'name': 'Name',
            'region': 'Region',
            'district': 'District',
            'capacity': 'Capacity',
            'manager': 'Manager',
            'products': 'Products',
            'date_created': 'Date Created',
            'date_modified': 'Last Updated'
        }

        df.rename(columns=column_map, inplace=True)

        file_name = f"Warehouses_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode('utf-8'))

        s3_url = upload_to_s3(file_data, file_name)
        if not s3_url:
            return

        group_names = [f'user_{user.id}']
        message = {
            "has_permission": True,
            "results": s3_url,
        }
        send_client_notification(
            message=message,
            message_type="export_notification",
            group_names=group_names
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Warehouse export failed: {str(e)}")