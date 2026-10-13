"""
ASGI config: HTTP goes to Django, WebSocket connections to the live-update consumers.
"""

import os

from django.core.asgi import get_asgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Project101.settings')

# Django must be set up before anything that imports models.
django_application = get_asgi_application()

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from apps.monitoring.routing import websocket_urlpatterns  # noqa: E402

application = ProtocolTypeRouter({
    'http': django_application,
    'websocket': AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
})
