import traceback
from urllib.parse import parse_qs

import sentry_sdk
from channels.auth import AuthMiddlewareStack
from channels.db import database_sync_to_async
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.db import close_old_connections
from jwt import DecodeError, ExpiredSignatureError, InvalidSignatureError, decode as jwt_decode

User = get_user_model()


class JWTAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        close_old_connections()
        qs = scope["query_string"].decode("utf8")
        if qs.startswith("?"):
            qs = qs[1:]
        params = parse_qs(qs)
        try:
            if token_list := params.get("token"):
                payload = self.get_payload(token_list[0])
                user = await self.get_logged_in_user(self.get_user_credentials(payload))
                scope["user"] = user
            else:
                scope["user"] = await self.get_logged_in_user(1)
        except (InvalidSignatureError, KeyError, ExpiredSignatureError, DecodeError) as e:
            sentry_sdk.capture_exception(e)
            traceback.print_exc()
            scope["user"] = AnonymousUser()
        except Exception as e:
            print("unexpected error:", e)
            scope["user"] = AnonymousUser()
        return await self.app(scope, receive, send)

    def get_payload(self, jwt_token):
        try:
            payload = jwt_decode(
                jwt_token, settings.SECRET_KEY, algorithms=["HS256"])
            return payload
        except DecodeError as e:
            print(str(e))
            return None

    def get_user_credentials(self, payload):
        """
        method to get user credentials from jwt token payload.
        defaults to user id.
        """
        user_id = payload['user_id']
        return user_id

    async def get_logged_in_user(self, user_id):
        user = await self.get_user(user_id)
        return user

    @database_sync_to_async
    def get_user(self, user_id):
        try:
            return User.objects.get(id=user_id)
        except User.DoesNotExist:
            return AnonymousUser()


def JWTAuthMiddlewareStack(app):
    return AuthMiddlewareStack(JWTAuthMiddleware(app))
