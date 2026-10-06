from fastapi.responses import JSONResponse
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder

from controllers import AuthController
from utils.schema_handler import SchemaHandler

class AuthResource:
    @SchemaHandler.validate("post_login.json")
    def on_post_login(self, payload: dict) -> JSONResponse:
        controller = AuthController()
        token_dto = controller.login_client(payload["document_number"], payload["password"])

        return JSONResponse(
            content=jsonable_encoder(token_dto),
            status_code=http_status.HTTP_200_OK
        )

    @SchemaHandler.validate("post_operator_login.json")
    def on_post_operator_login(self, payload: dict) -> JSONResponse:
        controller = AuthController()
        token_dto = controller.login_operator(payload["document_number"], payload["password"])

        return JSONResponse(
            content=jsonable_encoder(token_dto),
            status_code=http_status.HTTP_200_OK
        )

    def on_post_logout(self) -> JSONResponse:
        controller = AuthController()
        logout_dto = controller.logout()

        return JSONResponse(
            content=jsonable_encoder(logout_dto),
            status_code=http_status.HTTP_200_OK
        )