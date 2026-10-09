from os import environ

from tests.utils.requisition import ClientRequisition, BaseConnectorResponse


INTERNAL_TOKEN = environ.get("INTERNAL_TOKEN", "default_token")


class RequestGenerator:
    @staticmethod
    def POST_client(client_payload: dict) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "POST",
            "/client",
            payload=client_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN},
        )

        return response.response_status, response.response_json

    @staticmethod
    def POST_client_auth(client_payload: dict) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "POST",
            "/auth/login",
            payload=client_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN}
        )
        return response.response_status, response.response_json

    @staticmethod
    def GET_client(client_key: str, jwt_token: str) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "GET",
            f"/client/{client_key}",
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "Authorization": f"Bearer {jwt_token}"},
        )
        return response.response_status, response.response_json

    @staticmethod
    def PUT_client(client_key: str, jwt_token: str, update_payload: dict) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "PUT",
            f"/client/{client_key}",
            payload=update_payload,
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "Authorization": f"Bearer {jwt_token}"},
        )
        return response.response_status, response.response_json

    @staticmethod
    def GET_clients(params: dict = None) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "GET", "/clients", headers={"INTERNAL-TOKEN": INTERNAL_TOKEN}, query_params=params
        )
        return response.response_status, response.response_json

    @staticmethod
    def POST_account_deposit(account_key: str, jwt_token: str, idempotency_key:str, amount: int) -> BaseConnectorResponse:
        response = ClientRequisition.send(
            "POST",
            f"/account/{account_key}/deposit",
            payload={"amount": amount},
            headers={"INTERNAL-TOKEN": INTERNAL_TOKEN, "Authorization": f"Bearer {jwt_token}", "Idempotency-Key": idempotency_key},
        )
        return response.response_status, response.response_json
