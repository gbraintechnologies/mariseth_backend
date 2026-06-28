from datetime import datetime
from io import BytesIO, StringIO

import pandas as pd
import sentry_sdk
from celery import shared_task
from django.contrib.auth import get_user_model
from django.db.models import Q

from apps.credit.models import Credit, CreditPayback
from apps.credit.serializers.credits import CreditExportSerializer
from apps.credit.serializers.payback import PaybackExportSerializer
from apps.credit.utils import build_credit_filter_q, build_payback_filter_q
from apps.farm.models import Farm, Farmer, Product, FarmerRegistrationRequest
from apps.farm.serializers.farm import FarmExportSerializer
from apps.farm.serializers.farmer import FarmerExportSerializer
from apps.farm.serializers.farmer_reg_request import FarmerRegistrationRequestResponseSerializer
from apps.farm.serializers.products import ProductExportSerializer
from apps.farm.utils import (
    build_farm_filter_q,
    build_farmer_filter_q,
    build_product_filter_q, build_farmer_reg_filter_q,
)
from apps.inflow.models import InflowOrder
from apps.inflow.serializers import InflowOrderExportSerializer
from apps.inflow.utils import build_inflow_filter_q
from apps.outflow.models import OutflowOrder, OutflowOrderWarehouse
from apps.outflow.serializers.outflow import OutflowOrderExportSerializer
from apps.outflow.utils import build_outflow_filter_q
from apps.organizations.models import Organization
from apps.shared.consumers.notifications import send_client_notification
from apps.shared.utils.s3_upload import upload_to_s3
from apps.warehouse.models import Warehouse
from apps.warehouse.serializers import WarehouseExportSerializer
from apps.warehouse.utils import build_warehouse_filter_q
from mariseth.logging import logger

# New imports for employee export
from apps.hr.models import Employee, Training
from apps.hr.serializers.employee import EmployeeExportSerializer
from apps.hr.serializers.training import TrainingExportSerializer
from apps.hr.utils import build_employee_filter_q, build_training_filter_q

User = get_user_model()


@shared_task
def process_farm_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params["user_id"])
        organization = Organization.objects.get(pk=filter_params["organization_id"])
        farm_type = filter_params["farm_type"]
        filter_q = build_farm_filter_q(filter_params, organization)
        farms = (
            Farm.objects.select_related("created_by")
            .prefetch_related("farmproduct_set", "farmers")
            .filter(filter_q)
            .order_by("-date_created")
            .distinct()
        )
        serializer = FarmExportSerializer(farms, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        # Base column mapping
        column_map = {
            "farm_id": "Farm ID",
            "farm_type": "Farm Type",
            "name": "Farm Name",
            "location": "Location",
            "region": "Region",
            "district": "District",
            "size": "Size",
            "size_metric": "Size Unit",
            "land_ownership": "Land Ownership",
            "other_specification": "Ownership Details",
            "farmer": "Farmer",
            "created_by": "Created By",
            "date_created": "Date Created",
        }

        # Type-specific columns
        if farm_type == "internal":
            column_map.update(
                {
                    "irrigation": "Has Irrigation",
                    "use_of_fertilizers": "Fertilizer Use",
                    "farming_methods": "Farming Methods",
                    "provide_training": "Provides Training",
                    "government_ngo_support": "Receives Support",
                    "specify_support": "Support Details",
                    "areas_of_assistance": "Assistance Areas",
                }
            )
        elif farm_type == "external":
            column_map.update(
                {
                    "livestock_kept": "Livestock",
                    "has_access_to_market": "Market Access",
                    "type": "Farm Specialty",
                }
            )

        df.rename(columns=column_map, inplace=True)

        # Conditionally format columns based on farm type
        if farm_type == "internal":
            # Process JSON fields
            df["Fertilizer Use"] = df["Fertilizer Use"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else ""
            )
            df["Farming Methods"] = df["Farming Methods"].apply(
                lambda x: ", ".join(x) if isinstance(x, list) else ""
            )
            # Convert boolean to Yes/No
            df["Has Irrigation"] = df["Has Irrigation"].map({True: "Yes", False: "No"})
            df["Provides Training"] = df["Provides Training"].map(
                {True: "Yes", False: "No"}
            )
            df["Receives Support"] = df["Receives Support"].map(
                {True: "Yes", False: "No"}
            )
        elif farm_type == "external":
            # Process livestock data
            df["Livestock"] = df["Livestock"].apply(
                lambda x: x if isinstance(x, str) else ""
            )
            df["Market Access"] = df["Market Access"].map({True: "Yes", False: "No"})

        file_name = f"Farms_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return
        group_names = [f"user_{user.id}"]
        message = {
            "has_permission": True,
            "results": s3_url,
        }
        send_client_notification(
            message=message, message_type="export_notification", group_names=group_names
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Farm export failed: {str(e)}")


@shared_task
def process_product_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params["user_id"])
        organization = Organization.objects.get(pk=filter_params["organization_id"])

        filter_q = build_product_filter_q(filter_params, organization)
        product_type = filter_params["type"]

        products = (
            Product.objects.select_related(
                "category", "weight_metric", "quantity_metric", "created_by"
            )
            .filter(filter_q)
            .order_by("-date_created")
            .distinct()
        )

        serializer = ProductExportSerializer(products, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        column_map = {
            "product_id": "Product ID",
            "name": "Name",
            "type": "Type",
            "category": "Category",
            "weight": "Weight",
            "weight_metric": "Weight Unit",
            "quantity": "Quantity",
            "quantity_metric": "Quantity Unit",
            "season_status": "Season Status",
            "status": "Status",
            "season_start": "Season Start",
            "season_end": "Season End",
            "description": "Description",
            "breed": "Breed",
            "created_by": "Created By",
            "date_created": "Date Created",
            "last_updated": "Last Updated",
        }

        df.rename(columns=column_map, inplace=True)

        if product_type == "livestock":
            df["Weight"] = df["Weight"].apply(
                lambda x: f"{x} kg" if pd.notnull(x) else ""
            )
            df.drop(
                ["Season Start", "Season End", "Quantity Unit"], axis=1, inplace=True
            )
        elif product_type == "crops":
            df["Quantity"] = df["Quantity"].apply(
                lambda x: f"{x} bags" if pd.notnull(x) else ""
            )
            df.drop(["Breed", "Weight", "Weight Unit"], axis=1, inplace=True)

        file_name = f"Products_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return
        group_names = [f"user_{user.id}"]
        message = {
            "has_permission": True,
            "results": s3_url,
            "export_type": "product_export",
        }
        send_client_notification(
            message=message, message_type="export_notification", group_names=group_names
        )
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Product export failed: {str(e)}")


@shared_task
def process_farmer_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params["user_id"])
        organization = Organization.objects.get(pk=filter_params["organization_id"])

        filter_q = build_farmer_filter_q(filter_params, organization)

        farmers = (
            Farmer.objects.select_related(
                "farm", "lead_farmer", "created_by", "region", "district"
            )
            .filter(filter_q)
            .order_by("-date_created")
            .distinct()
        )

        serializer = FarmerExportSerializer(farmers, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        # Base column mapping
        column_map = {
            "farmer_id": "Farmer ID",
            "type": "Type",
            "first_name": "First Name",
            "last_name": "Last Name",
            "other_names": "Other Names",
            "gender": "Gender",
            "date_of_birth": "Date of Birth",
            "id_type": "ID Type",
            "id_number": "ID Number",
            "phone_number": "Phone Number",
            "email": "Email",
            "address": "Address",
            "village": "Village",
            "region": "Region",
            "district": "District",
            "country": "Country",
            "farm": "Farm",
            "lead_farmer": "Lead Farmer",
            "created_by": "Created By",
            "date_created": "Date Created",
        }

        df.rename(columns=column_map, inplace=True)

        file_name = f"Farmers_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return

        group_names = [f"user_{user.id}"]
        message = {
            "has_permission": True,
            "results": s3_url,
            "export_type": "farmer_export",
        }
        send_client_notification(
            message=message, message_type="export_notification", group_names=group_names
        )
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Farmer export failed: {str(e)}")

@shared_task
def process_farmer_reg_req_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params["user_id"])
        organization = Organization.objects.get(pk=filter_params["organization_id"])

        filter_q = build_farmer_reg_filter_q(filter_params, organization)

        farmer_reg_requests = (
            FarmerRegistrationRequest.objects.select_related(
                "reviewed_by", "region", "district"
            )
            .filter(filter_q)
            .order_by("-date_created")
            .distinct()
        )

        serializer = FarmerRegistrationRequestResponseSerializer(farmer_reg_requests, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        # Base column mapping
        column_map = {
            "id": "ID",
            "first_name": "First Name",
            "last_name": "Last Name",
            "gender": "Gender",
            "date_of_birth": "Date of Birth",
            "id_type": "ID Type",
            "id_number": "ID Number",
            "phone_number": "Phone Number",
            "email": "Email",
            "region": "Region",
            "district": "District",
            "country": "Country",
            "request_channel": "Request Channel",
            "status": "Status",
            "reviewed_by": "Approved By",
            "reviewed_at": "Approved At",
            "date_created": "Date Created",
        }

        df.rename(columns=column_map, inplace=True)

        file_name = f"Farmers_Registration_Request_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return

        group_names = [f"user_{user.id}"]
        message = {
            "has_permission": True,
            "results": s3_url,
            "export_type": "farmer_export",
        }
        send_client_notification(
            message=message, message_type="export_notification", group_names=group_names
        )
    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Farmer export failed: {str(e)}")

@shared_task
def process_credit_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params["user_id"])
        organization = Organization.objects.get(pk=filter_params["organization_id"])
        filter_q = build_credit_filter_q(filter_params, organization)

        credits = (
            Credit.objects.select_related("farmer")
            .filter(filter_q)
            .order_by("-issue_date")
        )

        serializer = CreditExportSerializer(credits, many=True)
        df = pd.DataFrame(serializer.data)
        column_map = {
            "id": "Credit ID",
            "farmer": "Farmer",
            "type": "Credit Type",
            "quantity": "Quantity",
            "credit_amount": "Credit Amount",
            "issue_date": "Issue Date",
            "due_date": "Due Date",
            "interest_rate": "Interest Rate (%)",
            "outstanding_amount": "Outstanding Amount",
            "payment_status": "Payment Status",
            "approval_status": "Approval Status",
            "main_crops": "Main Crops",
            "created_by": "Created By",
            "date_created": "Creation Date",
        }
        df.rename(columns=column_map, inplace=True)
        file_name = f"Credits_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return
        group_names = [f"user_{user.id}"]
        message = {
            "has_permission": True,
            "results": s3_url,
            "export_type": "credits_exports",
        }
        send_client_notification(
            message=message, message_type="export_notification", group_names=group_names
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Credit export failed: {str(e)}")


@shared_task
def process_warehouse_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params["user_id"])
        organization = Organization.objects.get(pk=filter_params["organization_id"])

        filter_q = build_warehouse_filter_q(filter_params, organization)

        warehouses = (
            Warehouse.objects.prefetch_related("managers")
            .filter(filter_q)
            .order_by("-date_created")
        )

        serializer = WarehouseExportSerializer(warehouses, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)
        column_map = {
            "warehouse_id": "Warehouse ID",
            "name": "Name",
            "region": "Region",
            "district": "District",
            "capacity": "Capacity",
            "managers": "Managers",
            "products": "Products",
            "date_created": "Date Created",
            "date_modified": "Last Updated",
        }

        df.rename(columns=column_map, inplace=True)

        file_name = f"Warehouses_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return

        group_names = [f"user_{user.id}"]
        message = {
            "has_permission": True,
            "results": s3_url,
            "export_type": "warehouse_export",
        }
        send_client_notification(
            message=message, message_type="export_notification", group_names=group_names
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Warehouse export failed: {str(e)}")


@shared_task
def process_inflow_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params["user_id"])
        organization = Organization.objects.get(pk=filter_params["organization_id"])

        filter_q = build_inflow_filter_q(filter_params, organization)

        inflow_orders = InflowOrder.objects.filter(filter_q).order_by("-order_creation_date")

        serializer = InflowOrderExportSerializer(inflow_orders, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        column_map = {
            "order_id": "Order ID",
            "aggregator": "Aggregator",
            "procurement_officer": "Procurement Officer",
            "destination_warehouse": "Destination Warehouse",
            "order_creation_date": "Order Creation Date",
            "expected_delivery_date": "Expected Delivery Date",
            "actual_delivery_date": "Actual Delivery Date",
            "status": "Status",
            "total_bags": "Total Bags",
            "order_total": "Order Total",
            "additional_costs": "Additional Costs",
            "additional_cost_amount": "Additional Cost Amount",
            "total_cost": "Total Cost",
            "total_products_cost": "Total Products Cost",
            "total_weight": "Total Weight",
            "comments": "Comments",
            "waybill_id": "Waybill ID",
            "date_created": "Date Created",
        }

        df.rename(columns=column_map, inplace=True)

        file_name = f"Inflow_Orders_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return

        group_names = [f"user_{user.id}"]
        message = {
            "has_permission": True,
            "results": s3_url,
            "export_type": "inflow_export",
        }
        send_client_notification(
            message=message, message_type="export_notification", group_names=group_names
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Inflow order export failed: {str(e)}")


@shared_task
def process_outflow_export(filter_params, approval=False):
    try:
        user = User.objects.get(pk=filter_params["user_id"])
        organization = Organization.objects.get(pk=filter_params["organization_id"])

        filter_q = build_outflow_filter_q(filter_params, organization)
        if not approval:
            outflow_orders = OutflowOrder.objects.filter(filter_q).order_by("-date_created")
        else:
            # Fetch OutflowOrderWarehouse objects
            outflow_warehouse_orders = OutflowOrderWarehouse.objects.select_related(
                'outflow_order', 'warehouse',
                'outflow_order__customer',
                'outflow_order__procurement_officer'
            ).filter(
                Q(outflow_order__in=OutflowOrder.objects.filter(
                    build_outflow_filter_q(filter_params, organization)
                )),
                warehouse__managers__in=[user]
            )
            # Extract the related OutflowOrder objects
            outflow_orders = [owh.outflow_order for owh in outflow_warehouse_orders]

        serializer = OutflowOrderExportSerializer(outflow_orders, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        column_map = {
            "order_id": "Order ID",
            "customer": "Customer",
            "procurement_officer": "Procurement Officer",
            "destination": "Destination",
            "expected_delivery_date": "Expected Delivery Date",
            "actual_delivery_date": "Actual Delivery Date",
            "status": "Status",
            "total_quantity": "Total Quantity",
            "total_cost": "Total Cost",
            "total_weight": "Total Weight",
            "additional_costs": "Additional Costs",
            "additional_cost_amount": "Additional Cost Amount",
            "extra_comments": "Extra Comments",
            "waybill_id": "Waybill ID",
            "date_created": "Date Created",
        }

        df.rename(columns=column_map, inplace=True)

        file_name = f"Outflow_Orders_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return

        group_names = [f"user_{user.id}"]
        message = {
            "has_permission": True,
            "results": s3_url,
            "export_type": "outflow_export",
        }
        send_client_notification(
            message=message, message_type="export_notification", group_names=group_names
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Outflow order export failed: {str(e)}")


@shared_task
def process_employee_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params["user_id"])
        organization = Organization.objects.get(pk=filter_params["organization_id"])

        filter_q = build_employee_filter_q(filter_params, organization)

        employees = (
            Employee.objects.select_related(
                "created_by", "contract__department", "contract__job_title"
            )
            .filter(filter_q)
            .order_by("-date_created")
        )

        serializer = EmployeeExportSerializer(employees, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        column_map = {
            "employee_id": "Employee ID",
            "first_name": "First Name",
            "last_name": "Last Name",
            "gender": "Gender",
            "relationship_status": "Relationship Status",
            "email": "Email",
            "phone_number": "Phone Number",
            "date_of_birth": "Date of Birth",
            "bank_account_number": "Bank Account Number",
            "status": "Status",
            "department": "Department",
            "job_title": "Job Title",
            "employment_type": "Employment Type",
            "work_type": "Work Type",
        }

        df.rename(columns=column_map, inplace=True)

        file_name = f"Employees_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return

        group_names = [f"user_{user.id}"]
        message = {
            "has_permission": True,
            "results": s3_url,
            "export_type": "employee_export",
        }
        send_client_notification(
            message=message, message_type="export_notification", group_names=group_names
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Employee export failed: {str(e)}")


@shared_task
def process_training_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params["user_id"])
        organization = Organization.objects.get(pk=filter_params["organization_id"])

        filter_q = build_training_filter_q(filter_params, organization)

        trainings = (
            Training.objects.select_related("created_by")
            .filter(filter_q)
            .order_by("-date_created")
        )

        serializer = TrainingExportSerializer(trainings, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        column_map = {
            "training_id": "Training ID",
            "title": "Title",
            "description": "Description",
            "training_type": "Training Type",
            "training_mode": "Training Mode",
            "start_date": "Start Date",
            "end_date": "End Date",
            "location": "Location",
            "material_url": "Material URL",
            "all_employees": "All Employees",
            "attendance_status": "Attendance Status",
            "created_by": "Created By",
            "date_created": "Date Created",
        }

        df.rename(columns=column_map, inplace=True)

        file_name = f"Trainings_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return

        group_names = [f"user_{user.id}"]
        message = {
            "has_permission": True,
            "results": s3_url,
            "export_type": "training_export",
        }
        send_client_notification(
            message=message, message_type="export_notification", group_names=group_names
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Training export failed: {str(e)}")


@shared_task
def process_payback_export(filter_params):
    try:
        user = User.objects.get(pk=filter_params["user_id"])
        organization = Organization.objects.get(pk=filter_params["organization_id"])

        filter_q = build_payback_filter_q(filter_params, organization)

        paybacks = (
            CreditPayback.objects.select_related("credit__farmer", "credit", "product")
            .filter(filter_q)
            .order_by("-date_created")
        )

        serializer = PaybackExportSerializer(paybacks, many=True)
        export_data = serializer.data

        df = pd.DataFrame(export_data)

        column_map = {
            "credit": "Credit ID",
            "farmer": "Farmer",
            "payback_method": "Payback Method",
            "amount": "Amount",
            "outstanding_before": "Outstanding Before",
            "outstanding_after": "Outstanding After",
            "product": "Product",
            "quantity_bags": "Quantity (Bags)",
            "comments": "Comments",
            "date_paid": "Date Paid",
            "status": "Status",
            "created_by": "Created By",
            "date_created": "Date Created",
        }

        df.rename(columns=column_map, inplace=True)

        file_name = f"Paybacks_Export_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.csv"
        csv_buffer = StringIO()
        df.to_csv(csv_buffer, index=False)
        file_data = BytesIO(csv_buffer.getvalue().encode("utf-8"))

        s3_url = upload_to_s3(file_data, file_name)

        if not s3_url:
            return

        group_names = [f"user_{user.id}"]
        message = {
            "has_permission": True,
            "results": s3_url,
            "export_type": "payback_export",
        }
        send_client_notification(
            message=message, message_type="export_notification", group_names=group_names
        )

    except Exception as e:
        sentry_sdk.capture_exception(e)
        logger.error(f"Payback export failed: {str(e)}")