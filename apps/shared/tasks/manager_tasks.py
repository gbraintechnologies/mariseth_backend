from celery import shared_task
from requests import HTTPError

from apps.shared.models import IntegrationLog
from apps.shared.services import MeshManagerAPIClient
from mariseth.logging import logger


def _handle_sync_success(log: IntegrationLog, response_data: dict):
    """
    Handles the success case of an API sync.
    Updates the log and the source object with the new manager ID.
    """
    source_object = log.content_object
    manager_id = response_data.get('Key')

    if not manager_id:
        # If the key is missing, treat it as a failure.
        log.status = IntegrationLog.Status.FAILED
        log.error_message = "API response did not contain a 'key' for manager_id."
        log.response_received = response_data
        log.save()
        logger.error(f"IntegrationLog {log.id}: {log.error_message}")
        return

    # Update the source object
    source_object.manager_id = manager_id
    source_object.manager_json_data = response_data
    source_object.save(update_fields=['manager_id', 'manager_json_data'])

    # Update the log
    log.status = IntegrationLog.Status.SUCCESS
    log.response_received = response_data
    log.error_message = None
    log.save()
    logger.info(f"Successfully synced {log.content_type.model} {source_object.id} to Manager.io with ID {manager_id}")


def _handle_sync_failure(task, log: IntegrationLog, exception: Exception):
    """
    Handles the failure case of an API sync.
    Logs the error and schedules a retry if possible.
    """
    log.status = IntegrationLog.Status.FAILED
    log.error_message = str(exception)
    log.retry_count = task.request.retries
    log.save()
    logger.error(f"Failed to sync IntegrationLog {log.id}. Error: {exception}")
    # Re-raise the exception to trigger Celery's retry mechanism
    raise task.retry(exc=exception)


@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 5) # Retry every 5 minutes
def sync_customer_to_manager(self, integration_log_id: int):
    """
    Celery task to synchronize a single Customer object to the Manager.io API.
    """
    try:
        log = IntegrationLog.objects.select_related('content_type').get(pk=integration_log_id)
    except IntegrationLog.DoesNotExist:
        logger.warning(f"IntegrationLog with id {integration_log_id} not found for sync.")
        return

    source_object = log.content_object
    if not source_object:
        log.status = IntegrationLog.Status.FAILED
        log.error_message = f"Source object (id: {log.object_id}) does not exist."
        log.save()
        return

    # Construct the payload from the Customer object
    payload = {
        "code": source_object.customer_id,
        "name": source_object.name,
        "email": source_object.email,
        "address": source_object.location,
        "billingAddress": source_object.location,
    }
    log.payload_sent = payload
    log.save(update_fields=['payload_sent'])

    try:
        client = MeshManagerAPIClient()
        response_data = client.create_customer(payload)
        _handle_sync_success(log, response_data)

    except HTTPError as exc:
        # Capture HTTP-specific errors (like 4xx, 5xx)
        response = exc.response
        log.response_received = {
            "status_code": response.status_code,
            "body": response.text,
        }
        _handle_sync_failure(self, log, exc)
    except Exception as exc:
        # Capture other exceptions (like network errors)
        _handle_sync_failure(self, log, exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 5)
def sync_inventory_item_to_manager(self, integration_log_id: int):
    """
    Celery task to synchronize a single Product object to the Manager.io API.
    """
    try:
        log = IntegrationLog.objects.select_related('content_type').get(pk=integration_log_id)
    except IntegrationLog.DoesNotExist:
        logger.warning(f"IntegrationLog with id {integration_log_id} not found for sync.")
        return

    source_object = log.content_object
    if not source_object:
        log.status = IntegrationLog.Status.FAILED
        log.error_message = f"Source object (id: {log.object_id}) does not exist."
        log.save()
        return

    # Construct the payload from the Product object
    payload = {
        "itemName": source_object.name,
        "itemCode": source_object.product_id,
        "unitName": source_object.category.name if source_object.category else None,
    }
    log.payload_sent = payload
    log.save(update_fields=['payload_sent'])

    try:
        client = MeshManagerAPIClient()
        response_data = client.create_inventory_item(payload)
        _handle_sync_success(log, response_data)

    except HTTPError as exc:
        response = exc.response
        log.response_received = {
            "status_code": response.status_code,
            "body": response.text,
        }
        _handle_sync_failure(self, log, exc)
    except Exception as exc:
        _handle_sync_failure(self, log, exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 5)
def sync_employee_to_manager(self, integration_log_id: int):
    """
    Celery task to synchronize a single Employee object to the Manager.io API.
    """
    try:
        log = IntegrationLog.objects.select_related('content_type').get(pk=integration_log_id)
    except IntegrationLog.DoesNotExist:
        logger.warning(f"IntegrationLog with id {integration_log_id} not found for sync.")
        return

    source_object = log.content_object
    if not source_object:
        log.status = IntegrationLog.Status.FAILED
        log.error_message = f"Source object (id: {log.object_id}) does not exist."
        log.save()
        return

    # Construct the payload from the Employee object
    # The Custom Field UUID is hardcoded as per the user's instruction.
    custom_field_uuid = "a12d2ca1-36d7-4ca7-89e2-29ed474ed40a"
    payload = {
        "code": source_object.employee_id,
        "name": f"{source_object.first_name} {source_object.last_name}",
        "email": source_object.email,
        "address": source_object.phone_number,  # Using phone as placeholder for address
        "CustomFields": {
            custom_field_uuid: source_object.ghana_card_number
        }
    }
    log.payload_sent = payload
    log.save(update_fields=['payload_sent'])

    try:
        client = MeshManagerAPIClient()
        response_data = client.create_employee(payload)
        _handle_sync_success(log, response_data)

    except HTTPError as exc:
        response = exc.response
        log.response_received = {
            "status_code": response.status_code,
            "body": response.text,
        }
        _handle_sync_failure(self, log, exc)
    except Exception as exc:
        _handle_sync_failure(self, log, exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 5)
def sync_supplier_to_manager(self, integration_log_id: int):
    """
    Celery task to synchronize a single Farm object (as a Supplier) to the Manager.io API.
    """
    try:
        log = IntegrationLog.objects.select_related('content_type').get(pk=integration_log_id)
    except IntegrationLog.DoesNotExist:
        logger.warning(f"IntegrationLog with id {integration_log_id} not found for sync.")
        return

    source_object = log.content_object
    if not source_object:
        log.status = IntegrationLog.Status.FAILED
        log.error_message = f"Source object (id: {log.object_id}) does not exist."
        log.save()
        return

    # Construct the payload from the Farm object
    address_parts = []
    if source_object.location: address_parts.append(source_object.location)
    if source_object.district: address_parts.append(source_object.district.name)
    if source_object.region: address_parts.append(source_object.region.name)
    if source_object.farmer and source_object.farmer.phone_number:
        address_parts.append(source_object.farmer.phone_number)
    address = ", ".join(address_parts)

    email = None
    if source_object.farmer and source_object.farmer.email:
        email = source_object.farmer.email

    payload = {
        "code": source_object.farm_id,
        "name": source_object.name,
        "address": address,
        "email": email,
    }
    log.payload_sent = payload
    log.save(update_fields=['payload_sent'])

    try:
        client = MeshManagerAPIClient()
        response_data = client.create_supplier(payload)
        _handle_sync_success(log, response_data)

    except HTTPError as exc:
        response = exc.response
        log.response_received = {
            "status_code": response.status_code,
            "body": response.text,
        }
        _handle_sync_failure(self, log, exc)
    except Exception as exc:
        _handle_sync_failure(self, log, exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 5)
def sync_purchase_invoice_to_manager(self, integration_log_id: int):
    """
    Celery task to synchronize a single InflowOrder object (as a Purchase Invoice) to the Manager.io API.
    """
    try:
        log = IntegrationLog.objects.select_related('content_type').get(pk=integration_log_id)
    except IntegrationLog.DoesNotExist:
        logger.warning(f"IntegrationLog with id {integration_log_id} not found for sync.")
        return

    source_object = log.content_object
    if not source_object:
        log.status = IntegrationLog.Status.FAILED
        log.error_message = f"Source object (id: {log.object_id}) does not exist."
        log.save()
        return

    # Hardcoded GL Account Key for additional costs (as discussed, should be configurable)
    ADDITIONAL_COST_GL_ACCOUNT = "bb9466e6-f72b-4a8c-a73e-3ee3cd68e9b7"

    # Construct Lines
    lines = []
    for order_product in source_object.products.all():
        if not order_product.product.manager_id:
            raise ValueError(f"Product {order_product.product.name} (ID: {order_product.product.id}) has no Manager.io ID.")
        if not order_product.farm.manager_id:
            raise ValueError(f"Farm {order_product.farm.name} (ID: {order_product.farm.id}) has no Manager.io ID.")

        lines.append({
            "Item": order_product.product.manager_id,
            "LineDescription": f"{order_product.product.name} received from {order_product.farm.name}",
            "qty": float(order_product.quantity),
            "PurchaseUnitPrice": float(order_product.unit_price),
        })

    # Add additional costs line if applicable
    if source_object.additional_cost_amount > 0:
        lines.append({
            "Account": ADDITIONAL_COST_GL_ACCOUNT,
            "LineDescription": source_object.additional_costs or "Additional costs",
            "qty": 1,
            "PurchaseUnitPrice": float(source_object.additional_cost_amount),
        })

    # Determine Supplier Key (using the farm of the first product for simplicity)
    supplier_key = None
    first_product = source_object.products.first()
    if first_product and first_product.farm and first_product.farm.manager_id:
        supplier_key = first_product.farm.manager_id
    else:
        raise ValueError(f"InflowOrder {source_object.order_id} has no associated supplier (Farm Manager.io ID).")

    payload = {
        "IssueDate": source_object.order_creation_date.isoformat(),
        "Reference": source_object.order_id,
        "Supplier": supplier_key,
        "Description": f"Aggregated products delivered to {source_object.destination_warehouse.name}",
        "Lines": lines,
        "HasLineNumber": True,
        "HasLineDescription": True,
    }
    log.payload_sent = payload
    log.save(update_fields=['payload_sent'])

    try:
        client = MeshManagerAPIClient()
        response_data = client.create_purchase_invoice(payload)
        _handle_sync_success(log, response_data)

    except HTTPError as exc:
        response = exc.response
        log.response_received = {
            "status_code": response.status_code,
            "body": response.text,
        }
        _handle_sync_failure(self, log, exc)
    except Exception as exc:
        _handle_sync_failure(self, log, exc)


@shared_task(bind=True, max_retries=3, default_retry_delay=60 * 5)
def sync_sales_invoice_to_manager(self, integration_log_id: int):
    """
    Celery task to synchronize a single OutflowOrder object (as a Sales Invoice) to the Manager.io API.
    """
    from datetime import timedelta

    try:
        log = IntegrationLog.objects.select_related('content_type').get(pk=integration_log_id)
    except IntegrationLog.DoesNotExist:
        logger.warning(f"IntegrationLog with id {integration_log_id} not found for sync.")
        return

    source_object = log.content_object
    if not source_object:
        log.status = IntegrationLog.Status.FAILED
        log.error_message = f"Source object (id: {log.object_id}) does not exist."
        log.save()
        return

    # Hardcoded GL Account Key for additional costs (as discussed, should be configurable)
    ADDITIONAL_COST_GL_ACCOUNT = "2a95df8f-f462-4d77-897b-5a34ce91600a" # Example from prompt

    # Construct Lines
    lines = []
    for order_warehouse in source_object.warehouses.all():
        for order_product in order_warehouse.products.all():
            if not order_product.product.manager_id:
                raise ValueError(f"Product {order_product.product.name} (ID: {order_product.product.id}) has no Manager.io ID.")

            lines.append({
                "Item": order_product.product.manager_id,
                "LineDescription": f"{order_product.product.name} from {order_warehouse.warehouse.name}",
                "Qty": float(order_product.expected_quantity),
                "SalesUnitPrice": float(order_product.price_per_unit),
            })

    # Add additional costs line if applicable
    if source_object.additional_cost_amount > 0:
        lines.append({
            "Account": ADDITIONAL_COST_GL_ACCOUNT,
            "LineDescription": source_object.additional_costs or "Cost of loading fee and transportation",
            "Qty": 1,
            "SalesUnitPrice": float(source_object.additional_cost_amount),
        })

    # Determine Customer Key
    if not source_object.customer.manager_id:
        raise ValueError(f"Customer {source_object.customer.name} (ID: {source_object.customer.id}) has no Manager.io ID.")
    customer_key = source_object.customer.manager_id

    # Calculate DueDateDate (e.g., 14 days after IssueDate)
    issue_date = source_object.date_created.date()
    due_date_date = issue_date + timedelta(days=14)

    payload = {
        "IssueDate": issue_date.isoformat(),
        "DueDate": 14, # Default to 14 days
        "DueDateDate": due_date_date.isoformat(),
        "Reference": source_object.order_id,
        "Customer": customer_key,
        "BillingAddress": source_object.destination, # Using destination as billing address
        "Description": f"Aggregated produce sold to {source_object.customer.name}",
        "Lines": lines,
        "HasLineNumber": True,
        "HasLineDescription": True,
    }
    log.payload_sent = payload
    log.save(update_fields=['payload_sent'])

    try:
        client = MeshManagerAPIClient()
        response_data = client.create_sales_invoice(payload)
        _handle_sync_success(log, response_data)

    except HTTPError as exc:
        response = exc.response
        log.response_received = {
            "status_code": response.status_code,
            "body": response.text,
        }
        _handle_sync_failure(self, log, exc)
    except Exception as exc:
        _handle_sync_failure(self, log, exc)
