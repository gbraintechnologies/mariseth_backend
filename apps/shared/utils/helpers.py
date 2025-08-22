import base64
from decimal import Decimal, ROUND_HALF_UP

from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist
from django.core.files.base import ContentFile
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
            return user
    except ObjectDoesNotExist:
        pass
    return None


def base64_to_image(image_data):
    """
    Decode the base64 image and save it in the TicketImage model.

    Args:
    image_data (str): The base64 encoded image data.
    """
    # Decoding the base64 string
    format, imgstr = image_data.split(';base64,')
    ext = format.split('/')[-1]
    image = ContentFile(base64.b64decode(imgstr), name='temp.' + ext)

    return image
