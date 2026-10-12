from os import environ
from typing import Optional

from tests.utils.requisition import ClientRequisition, BaseConnectorResponse


INTERNAL_TOKEN = environ.get("INTERNAL_TOKEN", "default_token")


class RequestGenerator:

    @staticmethod
    def build_headers(
        jwt_token: Optional[str] = None,
        idempotency_key: Optional[str] = None,
        internal_token: Optional[str] = INTERNAL_TOKEN,
        authorization: Optional[str] = None,
    ) -> dict:
        headers = {}
        if internal_token is not None:
            headers["INTERNAL-TOKEN"] = internal_token
        if authorization is not None:
            headers["Authorization"] = authorization
        elif jwt_token is not None:
            headers["Authorization"] = f"Bearer {jwt_token}"
        if idempotency_key is not None:
            headers["Idempotency-Key"] = idempotency_key
        return headers

    @staticmethod
    def send_raw(method: str, path: str, headers: dict = None, payload=None, params=None, data=None) -> BaseConnectorResponse:
        return ClientRequisition.send(method, path, payload=payload, headers=headers, query_params=params, data=data)

    @staticmethod
    def _send(method, path, payload=None, params=None, **header_kwargs):
        response = ClientRequisition.send(
            method,
            path,
            payload=payload,
            query_params=params,
            headers=RequestGenerator.build_headers(**header_kwargs),
        )
        return response.response_status, response.response_json

    @staticmethod
    def POST_client_auth(payload: dict, **header_kwargs):
        return RequestGenerator._send("POST", "/auth/login", payload=payload, **header_kwargs)

    @staticmethod
    def POST_operator_auth(payload: dict, **header_kwargs):
        return RequestGenerator._send("POST", "/auth/operator/login", payload=payload, **header_kwargs)

    @staticmethod
    def POST_logout(jwt_token: str, **header_kwargs):
        return RequestGenerator._send("POST", "/auth/logout", jwt_token=jwt_token, **header_kwargs)

    @staticmethod
    def POST_client(client_payload, **header_kwargs):
        return RequestGenerator._send("POST", "/client", payload=client_payload, **header_kwargs)

    @staticmethod
    def GET_client(client_key: str, jwt_token: Optional[str] = None, **header_kwargs):
        return RequestGenerator._send("GET", f"/client/{client_key}", jwt_token=jwt_token, **header_kwargs)

    @staticmethod
    def PUT_client(client_key: str, jwt_token: Optional[str], update_payload: dict, **header_kwargs):
        return RequestGenerator._send(
            "PUT", f"/client/{client_key}", payload=update_payload, jwt_token=jwt_token, **header_kwargs
        )

    @staticmethod
    def GET_clients(jwt_token: Optional[str], params: dict = None, **header_kwargs):
        return RequestGenerator._send("GET", "/clients", params=params, jwt_token=jwt_token, **header_kwargs)

    @staticmethod
    def POST_account_deposit(account_key: str, jwt_token: Optional[str], idempotency_key: Optional[str], amount, **header_kwargs):
        return RequestGenerator._send(
            "POST", f"/account/{account_key}/deposit",
            payload={"amount": amount}, jwt_token=jwt_token, idempotency_key=idempotency_key, **header_kwargs,
        )

    @staticmethod
    def POST_account_withdraw(account_key: str, jwt_token: Optional[str], idempotency_key: Optional[str], amount, **header_kwargs):
        return RequestGenerator._send(
            "POST", f"/account/{account_key}/withdraw",
            payload={"amount": amount}, jwt_token=jwt_token, idempotency_key=idempotency_key, **header_kwargs,
        )

    @staticmethod
    def POST_account_transfer(
        account_key_origin: str, account_key_destination, jwt_token: Optional[str],
        idempotency_key: Optional[str], amount, **header_kwargs,
    ):
        return RequestGenerator._send(
            "POST", f"/account/{account_key_origin}/transfer",
            payload={"account_to_key": account_key_destination, "amount": amount},
            jwt_token=jwt_token, idempotency_key=idempotency_key, **header_kwargs,
        )

    @staticmethod
    def GET_account_extract(account_key: str, jwt_token: Optional[str], params: dict = None, **header_kwargs):
        return RequestGenerator._send(
            "GET", f"/account/{account_key}/extract", params=params, jwt_token=jwt_token, **header_kwargs
        )

    @staticmethod
    def POST_credit(client_key: str, jwt_token: Optional[str], **header_kwargs):
        return RequestGenerator._send("POST", f"/client/{client_key}/credit", jwt_token=jwt_token, **header_kwargs)

    @staticmethod
    def POST_credit_withdraw(client_key: str, jwt_token: Optional[str], idempotency_key: Optional[str], amount, **header_kwargs):
        return RequestGenerator._send(
            "POST", f"/client/{client_key}/credit/withdraw",
            payload={"amount": amount}, jwt_token=jwt_token, idempotency_key=idempotency_key, **header_kwargs,
        )

    @staticmethod
    def POST_invoice_pay(client_key: str, jwt_token: Optional[str], idempotency_key: Optional[str], payload, **header_kwargs):
        return RequestGenerator._send(
            "POST", f"/client/{client_key}/invoice/pay",
            payload=payload, jwt_token=jwt_token, idempotency_key=idempotency_key, **header_kwargs,
        )
