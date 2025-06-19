from functools import wraps

from rest_framework import status
from rest_framework.response import Response

from apps.farm.models import Farmer


def superadmin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(view_instance, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return Response(
                {"error": "Authentication required"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        return view_func(view_instance, request, *args, **kwargs)

    return _wrapped_view


def lead_farmer_required(view_func):
    @wraps(view_func)
    def _wrapped_view(view_instance, request, *args, **kwargs):
        try:
            farmer_profile = request.user.farmer
        except Farmer.DoesNotExist:
            return Response(
                {"error": "User does not have a farmer profile."},
                status=status.HTTP_403_FORBIDDEN
            )
        if farmer_profile.type != 'lead':
            return Response(
                {"error": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(view_instance, request, *args, **kwargs)

    return _wrapped_view
