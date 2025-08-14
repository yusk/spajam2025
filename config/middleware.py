import json
import traceback

import jwt
from channels.db import database_sync_to_async
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin
from rest_framework.utils.serializer_helpers import ReturnDict

from main.models import User


class RequestHandleMiddleware(MiddlewareMixin):
    def process_request(self, request):
        pass

    def process_exception(self, request, exception):
        print(traceback.format_exc())

    def process_response(self, request, response):
        if response.status_code in [500]:
            message = "\n".join(
                ["【%s %s】" % (request.method, request.get_full_path()), "status_code: %s" % str(response.status_code)]
            )
            print(message)
        return response


class TokenAuthMiddleware:
    def __init__(self, app):
        self.app = app

    @staticmethod
    @database_sync_to_async
    def get_user_with_jwt(token):
        try:
            user_jwt = jwt.decode(
                token,
                settings.SECRET_KEY,
            )
            return User.objects.get(id=user_jwt["user_id"])
        except (KeyError, jwt.InvalidSignatureError, jwt.ExpiredSignatureError, jwt.DecodeError):
            traceback.print_exc()
        except Exception:
            traceback.print_exc()
        return None

    async def __call__(self, scope, receive, send):
        headers = dict(scope["headers"])
        auth_header = None
        secweb_header = None
        if b"sec-websocket-protocol" in headers:
            secweb_header = headers[b"sec-websocket-protocol"].decode()
            scope["subprotocol"] = secweb_header
        elif b"authorization" in headers:
            auth_header = headers[b"authorization"].decode()

        # Authorization
        if auth_header:
            auth_kind = None
            if len(auth_header.split(" ")) == 2:
                auth_kind, auth_value = auth_header.split(" ")
            if auth_kind == "JWT":
                user = await self.get_user_with_jwt(auth_value)
                if user:
                    scope["logged_in_user"] = user

        # Sec-Websocket-Protocol
        if secweb_header:
            user = self.get_user_with_jwt(secweb_header)
            if user:
                scope["logged_in_user"] = user

        # LatLong
        if b"latlong" in headers:
            latlong = headers[b"latlong"].decode()
            lat, long = map(float, latlong.split(","))
            scope["latlong"] = (lat, long)

        return await self.app(scope, receive, send)


class JsonErrorMessageMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        try:
            if response.status_code >= 400:
                if type(response.data) in [ReturnDict, dict]:
                    error_messages = []
                    for k, v in response.data.items():
                        if type(v) is list:
                            error_messages.append(f"{v[0]}({k})")
                        elif k == "detail":
                            error_messages.append(f"{v}")
                        else:
                            error_messages.append(f"{k}: {v}")
                    response.data["error_messages"] = error_messages
                response.content = json.dumps(response.data)
        except Exception:
            # traceback.print_exc()
            pass
        return response
