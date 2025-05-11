from django.db.models import Max

from apps.credit.models import Credit


def generate_credit_id(organization_id):
    """
    Generates farmer ID in format: F-{org_id:02}{sequence:03}
    Example: F-0200001
    """
    max_id = Credit.objects.filter(
        organization_id=organization_id
    ).aggregate(
        max_farmer_id=Max('credit_id')
    )['max_farmer_id']

    if max_id:
        try:
            sequence = int(max_id[-3:]) + 1
        except (ValueError, IndexError):
            sequence = 1
    else:
        sequence = 1

    return f"C-{int(organization_id):02}{sequence:03}"
