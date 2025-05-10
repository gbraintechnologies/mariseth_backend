from django.urls import path
from apps.shared.consumers import consumers

websocket_urlpatterns = [
    path('ws/engine', consumers.SharedSocketConsumer.as_asgi()),
]
