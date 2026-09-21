from fastapi import status as http_status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import AccountController
from utils.schema_handler import SchemaHandler

class AccountResource:

    @SchemaHandler.validate("post_deposit.json")
    def on_post_deposit(self, account_key:str, payload:dict) -> JSONResponse:
        controller = AccountController()

        account_dto = controller.deposit(account_key, payload["amount"])

        return JSONResponse(
            content=jsonable_encoder(account_dto),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate("post_withdraw.json")
    def on_post_withdraw(self, account_key: str, payload: dict) -> JSONResponse:
        controller = AccountController()

        account_dto = controller.withdraw(account_key, payload["amount"])

        return JSONResponse(
            content=jsonable_encoder(account_dto),
            status_code=http_status.HTTP_200_OK,
        )