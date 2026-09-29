from fastapi import status as http_status, Request
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import AccountController
from resources.client import DEFAULT_LIMIT, DEFAULT_PAGE
from utils.schema_handler import SchemaHandler

class AccountResource:

    @SchemaHandler.validate("post_deposit.json")
    def on_post_deposit(self, account_key:str, payload:dict, request: Request) -> JSONResponse:
        controller = AccountController()

        idempotency_key = request.headers.get("Idempotency-Key")
        account_dto = controller.deposit(account_key, payload["amount"], idempotency_key)

        return JSONResponse(
            content=jsonable_encoder(account_dto),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate("post_withdraw.json")
    def on_post_withdraw(self, account_key: str, payload: dict, request: Request) -> JSONResponse:
        controller = AccountController()

        idempotency_key = request.headers.get("Idempotency-Key")
        account_dto = controller.withdraw(account_key, payload["amount"], idempotency_key)

        return JSONResponse(
            content=jsonable_encoder(account_dto),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate("post_transfer.json")
    def on_post_transfer(self, account_key: str, payload: dict, request: Request) -> JSONResponse:
        controller = AccountController()

        idempotency_key = request.headers.get("Idempotency-Key")
        account_dto = controller.transfer(account_key, payload["account_to_key"], payload["amount"], idempotency_key)

        return JSONResponse(
            content=jsonable_encoder(account_dto),
            status_code=http_status.HTTP_200_OK,
        )

    @SchemaHandler.validate_query_params("get_extract.json")
    def on_get_extract(self, account_key: str, request: Request) -> JSONResponse:
        controller = AccountController()

        query_params = request.query_params

        limit = int(query_params.get("limit", DEFAULT_LIMIT))
        page = int(query_params.get("page", DEFAULT_PAGE))

        filters = {
            "start_date": query_params.get("start_date"),
            "end_date": query_params.get("end_date"),
        }

        offset = page * limit
        extract_result = controller.extract(account_key, limit, offset, filters)

        page_envelope = {
            "data": extract_result["account_extract"],
            "limit": limit,
            "page": page,
            "is_last_page": extract_result["is_last_page"],
        }

        return JSONResponse(
            content=jsonable_encoder(page_envelope),
            status_code=http_status.HTTP_200_OK,
        )