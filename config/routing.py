from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

from config.middleware import TokenAuthMiddleware
from room.consumers import RoomConsumer

TokenAuthMiddlewareStack = lambda inner: TokenAuthMiddleware(AuthMiddlewareStack(inner))

application = ProtocolTypeRouter(
    {
        "websocket": TokenAuthMiddlewareStack(
            URLRouter(
                [
                    path("ws/capsule/<str:pk>/", RoomConsumer.as_asgi()),
                ]
            )
        )
    }
)
