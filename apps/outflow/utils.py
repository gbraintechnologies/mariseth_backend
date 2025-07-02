import re

from apps.outflow.models import OutflowOrder


def generate_outflow_order_id(organization_id: int) -> str:
    org_part = f"{organization_id.id:02d}" if hasattr(organization_id, "id") else f"{organization_id:02d}"
    base_prefix = f"ORD-i{org_part}"

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


def generate_serial_number(warehouse_id: str, order_id: str, product_name: str, quantity: int) -> str:
    """
    Generate aggregated product serial numbers in the format:
    order_id/{warehouse_id}/{product_initials}/{start_number}-{end_number}

    Args:
        warehouse_id: Farm identifier (string or number)
        order_id: Order identifier
        product_name: Product name to extract initials from
        quantity: Number of bags/units

    Returns:
        Formatted serial number string
    """
    warehouse_part = str(warehouse_id).upper()
    product_initials = product_name[:2].upper() if product_name else 'XX'

    if quantity < 1:
        raise ValueError("Quantity must be at least 1")
    start = "001"
    end = f"{int(quantity):03d}"
    range_str = start if quantity == 1 else f"{start}-{end}"
    return f"{warehouse_part}/{product_initials}/{order_id}/{range_str}"
