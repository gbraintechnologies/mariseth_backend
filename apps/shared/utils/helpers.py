from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
from decimal import Decimal, ROUND_HALF_UP


def generate_tokens(user):
    """
    Generates access and refresh tokens for a given user.

    Args:
        user (User): The user for which tokens are generated.

    Returns:
        dict: A dictionary containing the access and refresh tokens.
    """
    refresh = RefreshToken.for_user(user)
    return {
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh)
    }


def format_decimal(value):
    if value is None:
        return None
    return Decimal(value).quantize(Decimal('0.00'), rounding=ROUND_HALF_UP)