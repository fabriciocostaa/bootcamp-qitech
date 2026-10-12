import jwt
from datetime import datetime, timezone
from uuid import UUID
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from constants import JWT_SECRET, BYPASS_ENDPOINTS, AUTH_BYPASS_ENDPOINTS
from database import get_context
from errors import qi_exception_to_response
from errors.custom_errors import InvalidCredentials
from repositories import TokenRepository

def register_auth_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def check_auth(request: Request, call_next):
        if request.url.path in BYPASS_ENDPOINTS + AUTH_BYPASS_ENDPOINTS:
            return await call_next(request)


        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return qi_exception_to_response(InvalidCredentials())

        token = auth_header.removeprefix("Bearer ")

        try:
            payload = jwt.decode(
                token, JWT_SECRET, algorithms=["HS256"],
                options={"require": ["exp", "jti", "subject_key", "type"]},
            )
            if (
                not isinstance(payload["jti"], str) or not payload["jti"]
                or not isinstance(payload["subject_key"], str) or not payload["subject_key"]
                or payload["type"] not in ("client", "operator")
                or not isinstance(payload["exp"], (int, float)) or isinstance(payload["exp"], bool)
            ):
                return qi_exception_to_response(InvalidCredentials())
            for claim in ("jti", "subject_key"):
                if str(UUID(payload[claim])) != payload[claim].lower():
                    return qi_exception_to_response(InvalidCredentials())
            datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        except (jwt.InvalidTokenError, TypeError, ValueError, OverflowError, OSError):
            return qi_exception_to_response(InvalidCredentials())

        context = get_context()
        token_repository = TokenRepository(context)

        if token_repository.is_revoked(payload["jti"]):
            return qi_exception_to_response(InvalidCredentials())
        if payload.get("type") == "client":
            context.authenticated_client_key = payload["subject_key"]
        elif payload.get("type") == "operator":
            context.authenticated_operator_key = payload["subject_key"]
        else:
            return qi_exception_to_response(InvalidCredentials())

        context.authenticated_jti = payload["jti"]
        context.authenticated_exp = payload["exp"]

        return await call_next(request)
