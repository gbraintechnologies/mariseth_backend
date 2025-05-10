import os

import django
os.environ.setdefault(
    'DJANGO_SETTINGS_MODULE',
    f"mariseth.settings.{os.environ.get('ENVIRONMENT', 'local')}"
)
django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

from apps.shared.consumers.middleware import JWTAuthMiddlewareStack
from mariseth.routing import websocket_urlpatterns  # Importing websocket_urlpatterns from routing.py

application = ProtocolTypeRouter({
    'http': get_asgi_application(),
    "websocket": JWTAuthMiddlewareStack(
        URLRouter(websocket_urlpatterns)
    ),
})
