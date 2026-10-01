from tests.utils.requisition import BaseConnectorResponse
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.request_generator import RequestGenerator


class ObjectGenerator:
    @staticmethod
    def create_client(hello: str = None) -> BaseConnectorResponse:

        client_payload = PayloadGenerator.create_client_payload()

        status, response = RequestGenerator.POST_client(client_payload)
        assert status == 201

        return response

    @staticmethod
    def update_client(client_key, new_status: str = None) -> BaseConnectorResponse:

        client_payload = PayloadGenerator.create_new_status_payload(new_status)

        status, response = RequestGenerator.PUT_client(client_key, client_payload)
        assert status == 202

        return response
