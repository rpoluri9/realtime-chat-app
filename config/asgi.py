"""ASGI entry point: HTTP + WebSocket routing."""
import os

from channels.routing import ProtocolTypeRouter, URLRouter
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from chat import routing as chat_routing  # noqa: E402
from chat.middleware import TokenAuthMiddleware  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": get_asgi_application(),
        "websocket": TokenAuthMiddleware(
            URLRouter(chat_routing.websocket_urlpatterns)
        ),
    }
)
