from functools import wraps

from rest_framework import status
from rest_framework.response import Response


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
