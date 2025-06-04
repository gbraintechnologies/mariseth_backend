from django.conf import settings
from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='admin/'), name='redirect-to-admin'),
    path('admin/', admin.site.urls),
    path('api/v1/', include('apps.accounts.urls')),
    path('api/v1/', include('apps.shared.urls')),
    path('api/v1/farm-management/', include('apps.farm.urls')),
    path('api/v1/', include('apps.credit.urls')),
    path('api/v1/', include('apps.customers.urls')),
    path('api/v1/', include('apps.warehouse.urls')),
    path('api/v1/', include('apps.inflow.urls')),
    path('api/v1/consumer/mobile', include('apps.consuner_mobile.urls')),
    # path('api/v1/admin/mobile', include('apps.admin_mobile.urls')),
]

if settings.ENVIRONMENT in ['local', 'staging']:
    urlpatterns += [path('', include('mariseth.swagger_urls'))]
