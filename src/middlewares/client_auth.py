import jwt
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from constants import JWT_SECRET, BYPASS_ENDPOINTS, AUTH_BYPASS_ENDPOINTS
from database import get_context
from errors import qi_exception_to_response
from errors.custom_errors import InvalidToken, UnauthorizedException, TokenExpiredException

def register_client_auth_middleware(application: FastAPI) -> None:
    @application.middleware("http")
    async def check_client_auth(request: Request, call_next):
        if request.url.path in BYPASS_ENDPOINTS + AUTH_BYPASS_ENDPOINTS:
            return await call_next(request)


        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return qi_exception_to_response(UnauthorizedException())

        token = auth_header.removeprefix("Bearer ")

        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        except jwt.ExpiredSignatureError:
            return qi_exception_to_response(TokenExpiredException())
        except jwt.InvalidTokenError:
            return qi_exception_to_response(InvalidToken())

        # Deixa no lugar combinado — o mesmo contextvars que o
        # session_manager usa. Quem vier depois (controller) pega
        # daqui, sem precisar receber isso por parâmetro.

        context = get_context()
        context.authenticated_client_key = payload["client_key"]

        return await call_next(request)