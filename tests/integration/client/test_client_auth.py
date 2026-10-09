from tests.utils import ObjectGenerator, PayloadGenerator, RandomGenerator, RequestGenerator


class TestClientLogin:
    """POST /auth/login — classes de equivalencia do corpo e das credenciais."""

    def test_login_returns_a_jwt(self):
        client = ObjectGenerator.create_client()
        payload = PayloadGenerator.create_client_auth_payload(client["document_number"], client["password"])

        status, response = RequestGenerator.POST_client_auth(payload)

        assert status == 200
        assert list(response.keys()) == ["token"]
        assert response["token"].count(".") == 2, "um JWT tem tres partes separadas por ponto"

    def test_token_opens_the_clients_own_data(self):
        client = ObjectGenerator.create_client()
        auth = ObjectGenerator.create_client_auth(client["document_number"], client["password"])

        status, response = RequestGenerator.GET_client(client["client_key"], auth["token"])

        assert status == 200
        assert response["client_key"] == client["client_key"]

    def test_two_logins_give_two_different_valid_tokens(self):
        client = ObjectGenerator.create_client()
        first = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]
        second = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]

        assert first != second
        for token in (first, second):
            status, _response = RequestGenerator.GET_client(client["client_key"], token)
            assert status == 200

    def test_refuses_empty_body(self):
        status, response = RequestGenerator.POST_client_auth({})
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_refuses_missing_document_number(self):
        status, response = RequestGenerator.POST_client_auth({"password": "senhamaria123"})
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_refuses_missing_password(self):
        payload = {"document_number": RandomGenerator.generate_cpf()}
        status, response = RequestGenerator.POST_client_auth(payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_refuses_null_document_number(self):
        payload = PayloadGenerator.create_client_auth_payload(document_number=None, password="senhamaria123")
        status, response = RequestGenerator.POST_client_auth(payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_refuses_unknown_field(self):
        client = ObjectGenerator.create_client()
        payload = PayloadGenerator.create_client_auth_payload(client["document_number"], client["password"])
        payload["campo_que_nao_existe"] = 1

        status, response = RequestGenerator.POST_client_auth(payload)

        assert status == 400
        assert response["code"] == "QIT000001"

    def test_refuses_malformed_document_number(self):
        for malformed in ["12345678901", "123.456.789-0", "abc.def.ghi-jk", "", " 123.456.789-09"]:
            payload = PayloadGenerator.create_client_auth_payload(malformed, "senhamaria123")
            status, response = RequestGenerator.POST_client_auth(payload)
            assert status == 400, f"aceitou o CPF torto {malformed!r}"
            assert response["code"] == "QIT000001"

    def test_password_length_boundaries(self):
        """Valor limite da senha: 7 e 256 caracteres sao recusados no formato (400)."""
        document_number = RandomGenerator.generate_cpf()
        for password in ["1234567", "a" * 256]:
            payload = PayloadGenerator.create_client_auth_payload(document_number, password)
            status, response = RequestGenerator.POST_client_auth(payload)
            assert status == 400, f"senha com {len(password)} caracteres passou do schema"
            assert response["code"] == "QIT000001"

    def test_refuses_non_string_fields(self):
        for payload in [
            {"document_number": 12345678909, "password": "senhamaria123"},
            {"document_number": RandomGenerator.generate_cpf(), "password": 12345678},
            {"document_number": ["x"], "password": "senhamaria123"},
        ]:
            status, response = RequestGenerator.POST_client_auth(payload)
            assert status == 400, payload
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

    def test_password_is_case_sensitive(self):
        client = ObjectGenerator.create_client()
        payload = PayloadGenerator.create_client_auth_payload(client["document_number"], client["password"].upper())

        status, response = RequestGenerator.POST_client_auth(payload)

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_unknown_document_number(self):
        payload = PayloadGenerator.create_client_auth_payload(RandomGenerator.generate_cpf(), "senhamaria123")

        status, response = RequestGenerator.POST_client_auth(payload)

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_wrong_password_and_unknown_user_are_indistinguishable(self):
        """Quem erra a senha e quem erra o CPF recebem a MESMA resposta.

        Se as mensagens fossem diferentes, a tela de login viraria um
        detector de CPFs cadastrados (enumeracao de usuarios).
        """
        client = ObjectGenerator.create_client()

        _status, wrong_password = RequestGenerator.POST_client_auth(
            PayloadGenerator.create_client_auth_payload(client["document_number"], "senha-errada-123")
        )
        _status, unknown_user = RequestGenerator.POST_client_auth(
            PayloadGenerator.create_client_auth_payload(RandomGenerator.generate_cpf(), "senha-errada-123")
        )

        assert wrong_password == unknown_user

    def test_sql_injection_in_password_is_just_a_wrong_password(self):
        client = ObjectGenerator.create_client()
        payload = PayloadGenerator.create_client_auth_payload(client["document_number"], "' OR '1'='1' --")

        status, response = RequestGenerator.POST_client_auth(payload)

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_does_not_accept_the_operators_credentials(self):
        """Operador e cliente sao populacoes separadas: o login de um nao abre o do outro."""
        from os import environ

        payload = PayloadGenerator.create_client_auth_payload(
            environ["ADMIN_DOCUMENT_NUMBER"], environ["ADMIN_INITIAL_PASSWORD"]
        )
        status, response = RequestGenerator.POST_client_auth(payload)

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_refuses_login_without_internal_token(self):
        client = ObjectGenerator.create_client()
        payload = PayloadGenerator.create_client_auth_payload(client["document_number"], client["password"])

        status, response = RequestGenerator.POST_client_auth(payload, internal_token=None)

        assert status == 403
        assert response["code"] == "QIT000002"

    def test_refuses_body_that_is_not_json(self):
        response = RequestGenerator.send_raw(
            "POST", "/auth/login",
            headers={**RequestGenerator.build_headers(), "Content-Type": "application/json"},
            data="isto nao e json",
        )
        assert response.response_status == 400
        assert response.response_json["code"] == "QIT000001"
