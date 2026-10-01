from tests.utils import RequestGenerator, PayloadGenerator

class TestClientAuth:
    def test_refuses_empty_body(self):
        payload = {}
        status, response = RequestGenerator.POST_client_auth(payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_refuses_missing_document_number(self):
        payload = PayloadGenerator.create_client_auth_payload(document_number=None, password="senhamaria123")

        status, response = RequestGenerator.POST_client_auth(payload)

        assert status == 400
        assert response["code"] == "QIT000001"

    def test_wrong_password(self):
        payload = PayloadGenerator.create_client_payload()
        document_number = payload["document_number"]
        status, response = RequestGenerator.POST_client(payload)
        assert status == 201

        payload = PayloadGenerator.create_client_auth_payload(document_number, password="wrong_password")

        status, response = RequestGenerator.POST_client_auth(payload)

        assert status == 401
        assert response["code"] == "QIT003001"