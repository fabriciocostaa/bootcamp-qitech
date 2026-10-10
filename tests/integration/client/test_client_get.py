from uuid import uuid4

import pytest

from tests.utils import ObjectGenerator, RequestGenerator


class TestClientGet:
    def test_not_found(self, operator_token):
        status, response = RequestGenerator.GET_client("00000000-0000-0000-0000-000000000000", operator_token)
        assert status == 404
        assert response["code"] == "QIT001001"

    def test_not_found_for_a_client_token_too(self):
        _client, token = ObjectGenerator.create_authenticated_client()

        status, response = RequestGenerator.GET_client(str(uuid4()), token)

        assert status == 404
        assert response["code"] == "QIT001001"

    @pytest.mark.parametrize("malformed_key", ["abc", "123", "00000000-0000-0000-0000", "' OR 1=1 --"])
    def test_malformed_key_is_not_found_and_never_a_500(self, operator_token, malformed_key):
        status, response = RequestGenerator.GET_client(malformed_key, operator_token)

        assert status == 404
        assert response["code"] == "QIT001001"

    def test_response_shape(self):
        client, token = ObjectGenerator.create_authenticated_client()

        status, response = RequestGenerator.GET_client(client["client_key"], token)

        assert status == 200
        assert sorted(response.keys()) == [
            "accounts", "birthdate", "client_key", "document_number", "email", "name", "status", "status_events",
        ]

    def test_client_reads_its_own_data(self):
        client, token = ObjectGenerator.create_authenticated_client()

        status, response = RequestGenerator.GET_client(client["client_key"], token)

        assert status == 200
        assert response["client_key"] == client["client_key"]

    def test_operator_reads_any_client(self, operator_token):
        client = ObjectGenerator.create_client()

        status, response = RequestGenerator.GET_client(client["client_key"], operator_token)

        assert status == 200
        assert response["document_number"] == client["document_number"]

    def test_client_cannot_read_another_client(self):
        """Um cliente nao enxerga os dados (nem o saldo) de outro."""
        _first, first_token = ObjectGenerator.create_authenticated_client()
        second = ObjectGenerator.create_client()

        status, response = RequestGenerator.GET_client(second["client_key"], first_token)

        assert status == 401
        assert response["code"] == "QIT003005"
        assert second["email"] not in str(response)
        assert second["document_number"] not in str(response)

    def test_requires_authentication(self):
        client = ObjectGenerator.create_client()

        status, response = RequestGenerator.GET_client(client["client_key"], None)

        assert status == 401
        assert response["code"] == "QIT003002"
