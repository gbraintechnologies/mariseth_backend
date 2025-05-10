import os
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.conf import settings


urlpatterns = [
    path('', RedirectView.as_view(url='admin/'), name='redirect-to-admin'),
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.shared.urls')),
    path('api/v1/farm-management/', include('apps.farm.urls')),
]

if settings.ENVIRONMENT in ['local', 'staging']:
    urlpatterns += [path('', include('mariseth.swagger_urls'))]