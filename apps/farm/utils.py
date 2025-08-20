from django.db.models import Max, Q

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


def build_farm_filter_q(params, organization):
    filter_q = Q(is_active=True, organization=organization)

    query = params.get('query')
    farm_type = params.get('farm_type')
    farm_size = params.get('farm_size')
    crop_type = params.get('crop_type')
    region = params.get('region')
    district = params.get('district')
    land_ownership = params.get('ownership_type') or params.get('land_ownership')
    date_from = params.get('date_from')
    date_to = params.get('date_to')

    if farm_type:
        filter_q &= Q(farm_type=farm_type)

    if farm_size:
        filter_q &= Q(farm_size=farm_size)

    if crop_type:
        filter_q &= Q(farmproduct__product__id=crop_type)

    if region:
        filter_q &= Q(region=region)

    if district:
        filter_q &= Q(district=district)

    if land_ownership:
        filter_q &= Q(land_ownership=land_ownership)

    if date_from and date_to:
        filter_q &= Q(date_created__date__range=[date_from, date_to])

    if query:
        filter_q &= (
                Q(name__icontains=query) |
                Q(farm_id__icontains=query) |
                Q(farmer__first_name__icontains=query) |
                Q(farmer__last_name__icontains=query)
        )

    return filter_q


def build_farmer_filter_q(params, organization):
    filter_q = Q(is_active=True, organization=organization)

    query = params.get('query')
    farmer_type = params.get('type') or params.get('farmer_type')
    ownership_type = params.get('ownership_type')
    country = params.get('country')
    region = params.get('region')
    district = params.get('district')
    lead = params.get('lead')
    date_from = params.get('start_date')
    date_to = params.get('end_date')

    if farmer_type:
        filter_q &= Q(type=farmer_type)

    if ownership_type:
        filter_q &= Q(farm__land_ownership=ownership_type)

    if country:
        filter_q &= Q(country__iexact=country)

    if region:
        filter_q &= Q(farm__region=region)

    if district:
        filter_q &= Q(farm__district=district)

    if lead:
        filter_q &= Q(lead_farmer__id=lead)

    if date_from and date_to:
        filter_q &= Q(date_created__date__range=[date_from, date_to])

    if query:
        filter_q &= (
            Q(first_name__icontains=query) |
            Q(last_name__icontains=query) |
            Q(phone_number__icontains=query[1:]) |
            Q(email__icontains=query) |
            Q(farm__name__icontains=query) |
            Q(farmer_id__icontains=query) |
            Q(id_number__icontains=query)
        )

    return filter_q


def build_product_filter_q(params, organization):
    filter_q = Q(is_active=True, organization=organization)

    query = params.get('query')
    product_type = params.get('type')
    category = params.get('category')
    status_filter = params.get('status')
    season_status = params.get('season_status')
    date_from = params.get('date_from') or params.get('start_date')
    date_to = params.get('date_to') or params.get('start_date')
    last_updated_from = params.get('last_updated_from')
    last_updated_to = params.get('last_updated_to')

    if product_type:
        filter_q &= Q(type=product_type)
    if category:
        filter_q &= Q(category_id=category)
    if status_filter:
        filter_q &= Q(status=status_filter)
    if season_status:
        filter_q &= Q(season_status=season_status)
    if date_from and date_to:
        filter_q &= Q(date_created__date__range=[date_from, date_to])
    if last_updated_from and last_updated_to:
        filter_q &= Q(last_updated__date__range=[last_updated_from, last_updated_to])

    if query:
        filter_q &= (
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(breed__icontains=query) |
            Q(color__icontains=query)
        )

    return filter_q