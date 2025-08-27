from django.db.models import Max, Q

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


def build_credit_filter_q(params, organization):
    filter_q = Q(is_active=True, organization=organization)

    query = params.get('query')
    payment_status = params.get('payment_status')
    type_param = params.get('type') or params.get('type_param')  # handle both
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    farmer = params.get('farmer')

    if query:
        filter_q &= (
                Q(id__icontains=query) |
                Q(credit_id__icontains=query) |
                Q(farmer__first_name__icontains=query) |
                Q(farmer__last_name__icontains=query)
        )

    if payment_status:
        filter_q &= Q(payment_status=payment_status.lower())

    if type_param:
        filter_q &= Q(type=type_param.lower())

    if farmer:
        filter_q &= Q(farmer__id=farmer)

    if start_date and end_date:
        filter_q &= Q(issue_date__range=[start_date, end_date])

    return filter_q


def build_payback_filter_q(params, organization):
    filter_q = Q(is_active=True, credit__organization=organization)

    query = params.get('query')
    credit_id = params.get('credit')
    payback_method = params.get('payback_method')
    start_date = params.get('start_date')
    end_date = params.get('end_date')
    status_filter = params.get('status')

    if query:
        filter_q &= (
            Q(credit__farmer__first_name__icontains=query) |
            Q(credit__farmer__last_name__icontains=query) |
            Q(credit__farmer__farmer_id__icontains=query) |
            Q(credit__credit_id__icontains=query) |
            Q(credit__farmer__phone_number__icontains=query[1:])
        )
    if credit_id:
        filter_q &= Q(credit_id=credit_id)
    if payback_method:
        filter_q &= Q(payback_method=payback_method)
    if start_date and end_date:
        filter_q &= Q(date_paid__range=[start_date, end_date])
    if status_filter:
        filter_q &= Q(status=status_filter)

    return filter_q
