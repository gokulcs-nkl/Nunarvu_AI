from django.urls import path

from .consumers import SessionConsumer

websocket_urlpatterns = [
    path('ws/sessions/<int:session_id>/', SessionConsumer.as_asgi()),
]
