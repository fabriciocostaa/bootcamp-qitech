from fastapi import status as http_status, Request
from fastapi import Header, Body
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from controllers import CreditController
from utils.schema_handler import SchemaHandler
from errors import IdempotencyKeyMissing

class CreditResource:
    

    def on_post(self, client_key: str) -> JSONResponse:
        controller = CreditController()
        
        credit_response = controller.request_credit(client_key)

        if credit_response.get("status") in ["REJECTED", "ERROR"]:
            return JSONResponse(
                content=jsonable_encoder(credit_response),
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return JSONResponse(
            content=jsonable_encoder(credit_response),
            status_code=http_status.HTTP_201_CREATED,
        )

    
    @SchemaHandler.validate("post_withdraw_credit.json")
    def on_post_withdraw(self, client_key: str, payload: dict, request: Request) -> JSONResponse:
        controller = CreditController()

        idempotency_key = request.headers.get("Idempotency-Key")
        if idempotency_key is None:
            raise IdempotencyKeyMissing()
        
        credit_response = controller.withdraw_credit(client_key, payload, idempotency_key)

        
        if credit_response.get("status") in ["REJECTED", "ERROR"]:
            return JSONResponse(
                content=jsonable_encoder(credit_response),
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return JSONResponse(
            content=jsonable_encoder(credit_response),
            status_code=http_status.HTTP_201_CREATED,
        )


    @SchemaHandler.validate("post_pay_invoice.json")
    def on_post_pay_invoice(self, client_key: str, payload: dict, request: Request) -> JSONResponse:
        controller = CreditController()

        idempotency_key = request.headers.get("Idempotency-Key")
        if idempotency_key is None:
            raise IdempotencyKeyMissing()
        
        credit_response = controller.pay_invoice(client_key, payload, idempotency_key)
        
        if credit_response.get("status") in ["REJECTED", "ERROR"]:
            return JSONResponse(
                content=jsonable_encoder(credit_response),
                status_code=http_status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        return JSONResponse(
            content=jsonable_encoder(credit_response),
            status_code=http_status.HTTP_200_OK,
        )