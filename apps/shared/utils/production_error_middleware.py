from django.conf import settings
from django.http import JsonResponse
import sentry_sdk

from mariseth.logging import logger


class ProductionErrorResponseMiddleware:
    """
    Return a generic message for uncaught server errors in production API requests.
    """

    GENERIC_MESSAGE = "An error occurred. Engineers have been notified."

    def __init__(self, get_response):
        self.get_response = get_response

    @staticmethod
    def _is_enabled():
        return getattr(settings, "ENVIRONMENT", "") == "production"

    @staticmethod
    def _is_api_request(request):
        return request.path.startswith("/api/")

    def __call__(self, request):
        try:
            response = self.get_response(request)
            if (
                self._is_enabled()
                and self._is_api_request(request)
                and getattr(response, "status_code", 200) >= 500
            ):
                return JsonResponse({"message": self.GENERIC_MESSAGE}, status=429)
            return response
        except Exception as exc:
            sentry_sdk.capture_exception(exc)
            logger.exception("Unhandled server error on path=%s", request.path)

            if self._is_enabled() and self._is_api_request(request):
                return JsonResponse({"message": self.GENERIC_MESSAGE}, status=429)

            raise
