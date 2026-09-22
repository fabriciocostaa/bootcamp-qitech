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

    @SchemaHandler.validate("post_transfer.json")
    def on_post_transfer(self, account_key: str, payload: dict) -> JSONResponse:
        controller = AccountController()

        account_dto = controller.transfer(account_key, payload["account_to_key"], payload["amount"])

        return JSONResponse(
            content=jsonable_encoder(account_dto),
            status_code=http_status.HTTP_200_OK,
        )

    def on_get_extract(self, account_key: str) -> JSONResponse:
        controller = AccountController()

        transfers_dto = controller.extract(account_key)

        return JSONResponse(
            content=jsonable_encoder(transfers_dto),
            status_code=http_status.HTTP_200_OK,
        )