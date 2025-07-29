import re
from datetime import datetime

from apps.outflow.models import OutflowOrder, OutflowOrderWarehouseHistory


def generate_outflow_order_id(organization_id: int) -> str:
    org_part = f"{organization_id.id:02d}" if hasattr(organization_id, "id") else f"{organization_id:02d}"
    base_prefix = f"ORD-o{org_part}"

    # Get all matching order_ids to find highest sequence
    existing_ids = OutflowOrder.objects.filter(
        organization_id=organization_id,
        order_id__startswith=base_prefix
    ).values_list('order_id', flat=True)

    # Extract numeric parts and find the next sequence
    max_sequence = 0
    for oid in existing_ids:
        match = re.fullmatch(rf"{base_prefix}(\d{{2}})", oid)
        if match:
            seq = int(match.group(1))
            max_sequence = max(max_sequence, seq)

    return f"{base_prefix}{max_sequence + 1:02d}"


def generate_serial_number(warehouse_id: str, order_id: str, product_id: str, quantity: int) -> str:
    """
    Generate aggregated product serial numbers in the format:
    order_id/{warehouse_id}/{product_initials}/{start_number}-{end_number}

    Args:
        warehouse_id: Farm identifier (string or number)
        order_id: Order identifier
        product_id: Product name to extract initials from
        quantity: Number of bags/units

    Returns:
        Formatted serial number string
    """
    if quantity < 1:
        raise ValueError("Quantity must be at least 1")
    start = "001"
    end = f"{int(quantity):03d}"
    range_str = start if quantity == 1 else f"{start}-{end}"
    return f"{warehouse_id}/{product_id}/{order_id}/{range_str}"


def create_warehouse_history(instance, field, old_value, new_value, user, product=None):
    OutflowOrderWarehouseHistory.objects.create(
        outflow_order_warehouse=instance,
        product=product,
        field=field,
        old_value=str(old_value) if old_value is not None else '',
        new_value=str(new_value) if new_value is not None else '',
        created_by=user
    )


def track_product_changes(product, old_data, new_data, instance, request):
    tracked_fields = ['status', 'available_quantity', 'reason', 'comments']
    for field in tracked_fields:
        old_val = old_data.get(field)
        new_val = new_data.get(field)
        # Only track if value actually changed
        if old_val != new_val:
            create_warehouse_history(
                instance=instance,
                field=f'product_{field}',
                old_value=old_val,
                new_value=new_val,
                user=request.user,
                product=product
            )


def generate_outflow_waybill_id(order_pk: int) -> str:
    """
    Generate waybill ID for OutflowOrder in format: WO-year-00{order_pk}
    """
    current_year = datetime.now().year
    return f"WO-{current_year}-00{order_pk}"


def generate_invoice_id(payment_pk: int) -> str:
    """
    Generate invoice ID for OutflowOrder in format: INV-2023-00{payment_pk}
    """
    current_year = datetime.now().year
    return f"INV-{current_year}-00{payment_pk}"