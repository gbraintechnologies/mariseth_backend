from django.core.cache import cache
from django.core.exceptions import ObjectDoesNotExist
from django.utils.deprecation import MiddlewareMixin
from rest_framework_simplejwt.authentication import JWTAuthentication

from apps.organizations.models import OrganizationUser


class AddOrganizationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if not hasattr(request, 'user') or request.user.is_anonymous:
            user = self._authenticate_user(request)
            if user:
                request.user = user
                self._set_organization_data(request, user)
            else:
                self._set_default_organization_data(request)

    def _authenticate_user(self, request):
        try:
            user_auth_tuple = JWTAuthentication().authenticate(request)
            return user_auth_tuple[0] if user_auth_tuple else None
        except Exception:
            return None
        
    def _set_organization_data(self, request, user):
        cache_key = f'organization_user_{user.id}'
        org_user = cache.get(cache_key)
        if not org_user:
            try:
                org_user = OrganizationUser.objects.select_related('organization').get(user=user)
                cache.set(cache_key, org_user, timeout=3600)
            except ObjectDoesNotExist:
                self._set_default_organization_data(request)
                return
        request.organization = org_user.organization

    def _set_default_organization_data(self, request):
        request.organization = None

    def process_response(self, request, response):
        return response
