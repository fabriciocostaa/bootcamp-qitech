from os import environ
from uuid import uuid4

from tests.utils.money import to_cents
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.random_generator import RandomGenerator, KYC_REJECTED_FRAGMENT
from tests.utils.request_generator import RequestGenerator


class ObjectGenerator:

    @staticmethod
    def create_client(**overrides) -> dict:
        client_payload = PayloadGenerator.create_client_payload(**overrides)

        status, response = RequestGenerator.POST_client(client_payload)
        assert status == 201, f"preparacao falhou: POST /client devolveu {status}: {response}"

        client = dict(client_payload)
        client["client_key"] = response["client_key"]
        return client

    @staticmethod
    def create_rejected_client() -> dict:
        return ObjectGenerator.create_client(
            document_number=RandomGenerator.generate_cpf_containing(KYC_REJECTED_FRAGMENT)
        )

    @staticmethod
    def create_client_auth(document_number: str, password: str = None) -> dict:
        client_payload = PayloadGenerator.create_client_auth_payload(
            document_number=document_number, password=password
        )

        status, response = RequestGenerator.POST_client_auth(client_payload)
        assert status == 200, f"preparacao falhou: login devolveu {status}: {response}"

        return response

    @staticmethod
    def create_authenticated_client() -> tuple:
        client = ObjectGenerator.create_client()
        auth = ObjectGenerator.create_client_auth(client["document_number"], client["password"])

        return client, auth["token"]

    @staticmethod
    def update_client(client_key: str, new_status: str, jwt_token: str) -> dict:
        client_payload = PayloadGenerator.create_new_status_payload(new_status)

        status, response = RequestGenerator.PUT_client(client_key, jwt_token, client_payload)
        assert status == 202, f"preparacao falhou: PUT /client devolveu {status}: {response}"

        return response

    @staticmethod
    def operator_token() -> str:
        payload = PayloadGenerator.create_client_auth_payload(
            document_number=environ["ADMIN_DOCUMENT_NUMBER"],
            password=environ["ADMIN_INITIAL_PASSWORD"],
        )
        status, response = RequestGenerator.POST_operator_auth(payload)
        assert status == 200, (
            f"preparacao falhou: login de operador devolveu {status}: {response}. "
            "O operador existe? (rode o seed do admin)"
        )
        return response["token"]

    @staticmethod
    def create_active_client(balance: int = 0) -> dict:
        client, token = ObjectGenerator.create_authenticated_client()
        client["token"] = token

        status, response = RequestGenerator.GET_client(client["client_key"], token)
        assert status == 200
        assert response["status"] == "approved", (
            f"o cliente deveria nascer aprovado e nasceu {response['status']} — o mock do KYC esta no ar?"
        )
        client["account_key"] = response["accounts"][0]["account_key"]

        if balance > 0:
            ObjectGenerator.deposit(client, balance)

        return client

    @staticmethod
    def deposit(client: dict, amount: int, idempotency_key: str = None) -> dict:
        status, response = RequestGenerator.POST_account_deposit(
            client["account_key"], client["token"], idempotency_key or str(uuid4()), amount
        )
        assert status == 200, f"preparacao falhou: deposito devolveu {status}: {response}"
        return response

    @staticmethod
    def get_balance(client: dict) -> int:
        status, response = RequestGenerator.GET_client(client["client_key"], client["token"])
        assert status == 200
        return to_cents(response["accounts"][0]["balance"])

    @staticmethod
    def get_balance_by_document(document_number: str, operator_token: str) -> int:
        status, response = RequestGenerator.GET_clients(operator_token, {"document_number": document_number})
        assert status == 200 and len(response["data"]) == 1
        status, response = RequestGenerator.GET_client(response["data"][0]["client_key"], operator_token)
        assert status == 200
        return to_cents(response["accounts"][0]["balance"])

    @staticmethod
    def open_credit_line(client: dict) -> dict:
        status, response = RequestGenerator.POST_credit(client["client_key"], client["token"])
        assert status == 201, f"preparacao falhou: pedido de credito devolveu {status}: {response}"
        return response
