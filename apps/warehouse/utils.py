from django.db.models import Max

from apps.warehouse.models import Warehouse


def generate_warehouse_id(organization_id):
    """
    Generates warehouse ID in format: W-{org_id:02}{sequence:03}
    Example: W-0200001
    """
    max_id = Warehouse.objects.filter(
        organization_id=organization_id
    ).aggregate(
        max_warehouse_id=Max('warehouse_id')
    )['max_warehouse_id']

    if max_id:
        try:
            sequence = int(max_id[-3:]) + 1
        except (ValueError, IndexError):
            sequence = 1
    else:
        sequence = 1

    return f"W-{int(organization_id):02}{sequence:03}"
