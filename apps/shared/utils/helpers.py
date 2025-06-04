from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from rest_framework_simplejwt.tokens import RefreshToken

User = get_user_model()

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


def authenticate(phone_number, pin):
    """
    Authenticate a user by phone number and PIN
    Returns user object if valid, None otherwise
    """
    try:
        user = User.objects.get(phone_number=phone_number, is_active=True)
        if user.check_password(pin):
            print(user, "////////////////////////////////")
            return user
    except ObjectDoesNotExist:
        pass
    return None
