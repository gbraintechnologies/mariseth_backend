import re
from datetime import datetime

from django.db.models import Max, Q

from .models import InflowOrder


def generate_serial_number(order_id: int,farm_id: str, product_id: str, quantity: int) -> str:
    """
    Generate aggregated product serial numbers in the format:
    {farm_id}/{product_initials}/{start_number}-{end_number}

    Args:
        order_id: Order identifier
        farm_id: Farm identifier (string or number)
        product_id: Product name to extract initials from
        quantity: Number of bags/units

    Returns:
        Formatted serial number string
    """
    farm_part = str(farm_id).upper()

    if quantity < 1:
        raise ValueError("Quantity must be at least 1")
    start = "001"
    end = f"{int(quantity):03d}"
    range_str = start if quantity == 1 else f"{start}-{end}"
    return f"{farm_part}/{product_id}/{order_id}/{range_str}"


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


def generate_inflow_waybill_id(order_pk: int) -> str:
    """
    Generate waybill ID for InflowOrder in format: WI-year-00{order_pk}
    """
    current_year = datetime.now().year
    return f"WI-{current_year}-00{order_pk}"


def build_inflow_filter_q(filter_params, organization):
    filter_q = Q(is_active=True, organization=organization)

    status_filter = filter_params.get('status')
    warehouse = filter_params.get('warehouse')
    start_date = filter_params.get('start_date')
    end_date = filter_params.get('end_date')
    query = filter_params.get('query')
    completed = filter_params.get('completed', 'false').lower()

    if completed == 'true':
        filter_q &= Q(status='approved')
    else:
        filter_q &= ~Q(status='approved')
    if status_filter:
        filter_q &= Q(status=status_filter)
    if warehouse:
        filter_q &= Q(destination_warehouse=warehouse)
    if start_date and end_date:
        filter_q &= Q(date_created__date__gte=start_date, date_created__date__lte=end_date)
    elif start_date:
        filter_q &= Q(date_created__date__gte=start_date)
    elif end_date:
        filter_q &= Q(date_created__date__lte=end_date)
    if query:
        filter_q &= (
                Q(order_id__icontains=query) |
                Q(aggregator__first_name__icontains=query) |
                Q(aggregator__last_name__icontains=query)
        )
    return filter_q
