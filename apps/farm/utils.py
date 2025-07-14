from django.db.models import Max

from apps.farm.models import Farm, Farmer, Product


def generate_farm_id(name):
    """
    Generates farm ID in format: {initials}{sequence}
    Example: AB1
    """
    initials = ''.join(word[0].upper() for word in name.split())
    base_id = initials
    i = 1
    while Farm.objects.filter(farm_id=base_id).exists():
        base_id = f"{initials}{i}"
        i += 1
    return base_id


def generate_farmer_id(organization_id):
    """
    Generates farmer ID in format: F-{org_id:02}{sequence:03}
    Example: F-0200001
    """
    max_id = Farmer.objects.filter(
        organization_id=organization_id
    ).aggregate(
        max_farmer_id=Max('farmer_id')
    )['max_farmer_id']

    if max_id:
        try:
            sequence = int(max_id[-3:]) + 1
        except (ValueError, IndexError):
            sequence = 1
    else:
        sequence = 1

    return f"F-{int(organization_id):02}{sequence:03}"


def generate_product_id(org_id, product_type):
    """
    Generates product ID in format: {type_prefix}-{org_id:02}{sequence:05}
    Example: C-0200001 for org_id=2's first crop
             L-0200001 for org_id=2's first livestock
    """
    prefix = 'C' if product_type == 'crop' else 'L'

    # get the last-created product for this org/type
    last_obj = (
        Product.objects
        .filter(organization_id=org_id, type=product_type)
        .order_by('date_created')
        .last()
    )
    if last_obj and '-' in last_obj.product_id:
        tail = last_obj.product_id.split('-', 1)[1]
        seq = int(tail) + 1
        width = len(tail)
    else:
        # first-ever: ORGID (2 digits) + three zeros → then +1
        org_part = f"{int(org_id):02}"
        default_numeric = org_part + "0" * 3
        width = len(default_numeric)
        seq = int(default_numeric) + 1

    return f"{prefix}-{seq:0{width}d}"

