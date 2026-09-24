from fastapi.responses import JSONResponse
from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder

from controllers import AuthController
from utils.schema_handler import SchemaHandler

class AuthResource:
    @SchemaHandler.validate("post_login.json")
    def on_post_login(self, payload: dict) -> JSONResponse:
        controller = AuthController()
        token_dto = controller.login(payload["document_number"], payload["password"])

        return JSONResponse(
            content=jsonable_encoder(token_dto),
            status_code=http_status.HTTP_200_OK
        )