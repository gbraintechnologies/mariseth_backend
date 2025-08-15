from django.db.models import Max, Q

from apps.warehouse.models import Warehouse


def generate_warehouse_id(warehouse_name):
    """
    Generates warehouse ID based on warehouse name:
    - Single word: First 2 letters capitalized (e.g., "Onion" -> "ON")
    - Multiple words: First letter of each word capitalized (e.g., "Garden Eggs" -> "GE")
    - If duplicate exists: Add sequence number (e.g., "GE-1", "GE-2")
    """
    words = warehouse_name.split()
    if len(words) == 1:
        # Single word: take first 2 letters
        initials = warehouse_name[:2].upper()
    else:
        # Multiple words: take first letter of each word
        initials = ''.join(word[0].upper() for word in words)
    # Check if any warehouse already exists with these initials
    existing_warehouses = Warehouse.objects.filter(warehouse_id__startswith=initials)

    if existing_warehouses.exists():
        # If this is the first duplicate, it should be initials-1
        # If others exist, increment the highest sequence
        max_sequence = 0
        for warehouse in existing_warehouses:
            if '-' in warehouse.warehouse_id:
                try:
                    sequence = int(warehouse.warehouse_id.split('-')[-1])
                    max_sequence = max(max_sequence, sequence)
                except ValueError:
                    continue
        sequence = max_sequence + 1
        return f"{initials}-{sequence}"
    else:
        # First occurrence - no sequence number
        return initials


def build_warehouse_filter_q(filter_params, organization):
    query = filter_params.get('query')
    region = filter_params.get('region')
    district = filter_params.get('district')
    date_from = filter_params.get('start_date')
    date_to = filter_params.get('end_date')

    filter_q = Q(is_active=True, organization=organization)

    if region:
        filter_q &= Q(region=region)
    if district:
        filter_q &= Q(district=district)
    if date_from and date_to:
        filter_q &= Q(date_created__date__range=[date_from, date_to])
    if query:
        filter_q &= (
            Q(name__icontains=query) |
            Q(warehouse_id__icontains=query)
        )

    return filter_q
