from os import environ

from tests.utils import ObjectGenerator, PayloadGenerator, RandomGenerator, RequestGenerator


def operator_payload(**overrides) -> dict:
    payload = PayloadGenerator.create_client_auth_payload(
        environ["ADMIN_DOCUMENT_NUMBER"], environ["ADMIN_INITIAL_PASSWORD"]
    )
    payload.update(overrides)
    return payload


class TestOperatorLogin:
    """POST /auth/operator/login"""

    def test_operator_login_returns_a_jwt(self):
        status, response = RequestGenerator.POST_operator_auth(operator_payload())

        assert status == 200
        assert response["token"].count(".") == 2

    def test_operator_token_opens_the_client_listing(self, operator_token):
        status, response = RequestGenerator.GET_clients(operator_token)

        assert status == 200
        assert "data" in response

    def test_wrong_password(self):
        status, response = RequestGenerator.POST_operator_auth(operator_payload(password="senha-errada-123"))

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_unknown_document_number(self):
        status, response = RequestGenerator.POST_operator_auth(
            operator_payload(document_number=RandomGenerator.generate_cpf())
        )

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_does_not_accept_a_clients_credentials(self):
        client = ObjectGenerator.create_client()

        status, response = RequestGenerator.POST_operator_auth(
            PayloadGenerator.create_client_auth_payload(client["document_number"], client["password"])
        )

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_refuses_empty_body(self):
        status, response = RequestGenerator.POST_operator_auth({})
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_refuses_malformed_fields(self):
        for payload in [
            operator_payload(document_number="12345678901"),
            operator_payload(password="curta"),
            {**operator_payload(), "extra": 1},
        ]:
            status, response = RequestGenerator.POST_operator_auth(payload)
            assert status == 400, payload
            assert response["code"] == "QIT000001"

    def test_refuses_login_without_internal_token(self):
        status, response = RequestGenerator.POST_operator_auth(operator_payload(), internal_token=None)

        assert status == 403
        assert response["code"] == "QIT000002"
