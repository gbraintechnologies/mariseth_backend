import re

from django.db.models import Max

from .models import InflowOrder


def generate_serial_number(farm_id: str, product_name: str, quantity: int) -> str:
    """
    Generate aggregated product serial numbers in the format:
    {farm_id}/{product_initials}/{start_number}-{end_number}

    Args:
        farm_id: Farm identifier (string or number)
        product_name: Product name to extract initials from
        quantity: Number of bags/units

    Returns:
        Formatted serial number string
    """
    farm_part = str(farm_id).upper()
    product_initials = product_name[:2].upper() if product_name else 'XX'

    if quantity < 1:
        raise ValueError("Quantity must be at least 1")
    start = "001"
    end = f"{int(quantity):03d}"
    range_str = start if quantity == 1 else f"{start}-{end}"
    return f"{farm_part}/{product_initials}/{range_str}"


def generate_order_id(organization_id: int) -> str:
    """
    Generate order ID in format: ORD-i{org_id:02d}{sequence:02d}
    Example: ORD-i0101 for org_id=1, first order
    """
    org_part = f"{organization_id.id:02d}" if hasattr(organization_id, "id") else f"{organization_id:02d}"
    last_id = InflowOrder.objects.filter(
        organization_id=organization_id,
        order_id__startswith=f"ORD-i{org_part}"
    ).aggregate(
        max_id=Max('order_id')
    )['max_id']

    if last_id:
        match = re.search(rf"ORD-i{org_part}(\d{{2}})", last_id)
        sequence = int(match.group(1)) + 1 if match else 1
    else:
        sequence = 1

    return f"ORD-i{org_part}{sequence:02d}"
