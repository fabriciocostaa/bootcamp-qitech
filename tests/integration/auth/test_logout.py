from tests.utils import ObjectGenerator, RequestGenerator


class TestLogout:
    """POST /auth/logout — o token sai de circulacao na hora, nao so quando expira."""

    def test_logout_succeeds(self):
        _client, token = ObjectGenerator.create_authenticated_client()

        status, response = RequestGenerator.POST_logout(token)

        assert status == 200
        assert "message" in response

    def test_token_stops_working_after_logout(self):
        client, token = ObjectGenerator.create_authenticated_client()
        status, _response = RequestGenerator.GET_client(client["client_key"], token)
        assert status == 200

        status, _response = RequestGenerator.POST_logout(token)
        assert status == 200

        status, response = RequestGenerator.GET_client(client["client_key"], token)
        assert status == 401
        assert response["code"] == "QIT003004"

    def test_logout_twice_with_the_same_token_is_refused(self):
        _client, token = ObjectGenerator.create_authenticated_client()
        RequestGenerator.POST_logout(token)

        status, response = RequestGenerator.POST_logout(token)

        assert status == 401
        assert response["code"] == "QIT003004"

    def test_logout_revokes_only_that_token(self):
        """Sair de um aparelho nao derruba os outros: cada login tem o seu token."""
        client = ObjectGenerator.create_client()
        phone = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]
        laptop = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]

        status, _response = RequestGenerator.POST_logout(phone)
        assert status == 200

        status, _response = RequestGenerator.GET_client(client["client_key"], laptop)
        assert status == 200

    def test_logout_does_not_affect_other_users(self):
        first, first_token = ObjectGenerator.create_authenticated_client()
        second, second_token = ObjectGenerator.create_authenticated_client()

        RequestGenerator.POST_logout(first_token)

        status, _response = RequestGenerator.GET_client(second["client_key"], second_token)
        assert status == 200

    def test_can_login_again_after_logout(self):
        client = ObjectGenerator.create_client()
        old = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]
        RequestGenerator.POST_logout(old)

        new = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]

        status, _response = RequestGenerator.GET_client(client["client_key"], new)
        assert status == 200

    def test_operator_can_logout(self, operator_token):
        status, _response = RequestGenerator.POST_logout(operator_token)
        assert status == 200

        status, response = RequestGenerator.GET_clients(operator_token)
        assert status == 401
        assert response["code"] == "QIT003004"

    def test_logout_without_token_is_refused(self):
        status, response = RequestGenerator.POST_logout(None)

        assert status == 401
        assert response["code"] == "QIT003002"
