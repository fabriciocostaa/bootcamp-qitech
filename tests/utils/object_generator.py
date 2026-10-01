from tests.utils.requisition import BaseConnectorResponse
from tests.utils.payload_generator import PayloadGenerator
from tests.utils.request_generator import RequestGenerator


class ObjectGenerator:
    @staticmethod
    def create_client() -> dict:
        """Cria um cliente e devolve os dados que foram enviados + a client_key.
 
        O POST /client devolve SO a client_key (clientDTO.only_obj_key).
        Por isso o teste precisa guardar o payload que enviou: e ele a
        fonte da verdade pra comparar com o GET depois.
        """
        client_payload = PayloadGenerator.create_client_payload()
 
        status, response = RequestGenerator.POST_client(client_payload)
        assert status == 201
 
        client = dict(client_payload)
        client["client_key"] = response["client_key"]
        return client

    @staticmethod
    def update_client(client_key, new_status: str = None, jwt_token: str = None) -> BaseConnectorResponse:

        client_payload = PayloadGenerator.create_new_status_payload(new_status)

        status, response = RequestGenerator.PUT_client(client_key, jwt_token, client_payload)
        assert status == 202

        return response

    @staticmethod
    def create_client_auth(document_number: str, password: str = None) -> BaseConnectorResponse:

        client_payload = PayloadGenerator.create_client_auth_payload(
            document_number=document_number,
            password=password
        )

        status, response = RequestGenerator.POST_client_auth(client_payload)
        assert status == 200

        return response

    @staticmethod
    def create_authenticated_client() -> dict:
        """Cria um cliente e devolve os dados que foram enviados + a client_key + jwt_token.
        """
        client = ObjectGenerator.create_client()
        auth = ObjectGenerator.create_client_auth(client["document_number"], client["password"])
        
        return client, auth["token"]
