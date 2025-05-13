from django.db.models import Max

from apps.customers.models import Customer


def generate_customer_id(organization_id):
    """
    Generates farmer ID in format: C-{org_id:02}{sequence:03}
    Example: C-0200001
    """
    max_id = Customer.objects.filter(
        organization_id=organization_id
    ).aggregate(
        max_customer_id=Max('customer_id')
    )['max_customer_id']

    if max_id:
        try:
            sequence = int(max_id[-3:]) + 1
        except (ValueError, IndexError):
            sequence = 1
    else:
        sequence = 1

    return f"C-{int(organization_id):02}{sequence:03}"
