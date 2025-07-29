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


def generate_product_id(product_name):
    """
    Generates product ID based on product name:
    - Single word: First 2 letters capitalized (e.g., "Onion" -> "ON")
    - Multiple words: First letter of each word capitalized (e.g., "Garden Eggs" -> "GE")
    - If duplicate exists: Add sequence number (e.g., "GE-1", "GE-2")
    """
    words = product_name.split()
    if len(words) == 1:
        # Single word: take first 2 letters
        initials = product_name[:2].upper()
    else:
        # Multiple words: take first letter of each word
        initials = ''.join(word[0].upper() for word in words)

    # Check if any product already exists with these initials
    existing_products = Product.objects.filter(product_id__startswith=initials)
    if existing_products.exists():
        # If this is the first duplicate, it should be initials-1
        # If others exist, increment the highest sequence
        max_sequence = 0
        for product in existing_products:
            if '-' in product.product_id:
                try:
                    sequence = int(product.product_id.split('-')[-1])
                    max_sequence = max(max_sequence, sequence)
                except ValueError:
                    continue

        sequence = max_sequence + 1
        return f"{initials}-{sequence}"
    else:
        # First occurrence - no sequence number
        return initials

