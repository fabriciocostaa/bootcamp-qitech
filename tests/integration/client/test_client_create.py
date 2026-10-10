from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from tests.utils import ObjectGenerator, PayloadGenerator, RandomGenerator, RequestGenerator
from tests.utils.markers import known_bug
from tests.utils.random_generator import KYC_REJECTED_FRAGMENT

REQUIRED_FIELDS = ["name", "email", "document_number", "password", "birthdate"]


class TestClientCreateSchema:
    """O que o schema (src/schemas/post_client.json) barra: 400 + QIT000001."""

    def test_refuses_empty_body(self):
        payload = {}
        status, response = RequestGenerator.POST_client(payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    @pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
    def test_refuses_each_missing_required_field(self, missing_field):
        """Um campo faltando por vez: cada um dos cinco e obrigatorio."""
        payload = PayloadGenerator.create_client_payload()
        del payload[missing_field]

        status, response = RequestGenerator.POST_client(payload)

        assert status == 400, f"aceitou o cadastro sem '{missing_field}'"
        assert response["code"] == "QIT000001"

    def test_schema_refuses_unknown_field(self):
        """Campo que o schema nao pediu e erro, nao um campo ignorado.

        Quem escreve `{"hllo": "mundo"}` com erro de digitacao prefere
        receber um 400 agora a descobrir amanha que o campo nunca chegou.
        Quem garante isso e o "additionalProperties": false do
        src/schemas/post_client.json.
        """
        payload = PayloadGenerator.create_client_payload()
        payload["campo_que_nao_existe"] = 1

        status, response = RequestGenerator.POST_client(payload)
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_schema_refuses_malformed_person_fields(self):
        """Cada campo de pessoa tem um formato, e o schema cobra os tres.

        Estao juntos num teste so porque sao a MESMA regra vista varias
        vezes: um `pattern` no src/schemas/post_client.json. Cada volta do
        laco derruba um deles e mantem os outros certos — assim, quando
        este teste ficar vermelho, a mensagem diz qual formato parou de
        ser cobrado.

        O `pattern` nao e frescura: o `format` do JSON Schema ("email",
        "date") NAO valida nada na biblioteca que este projeto usa. Ele e
        so uma anotacao. Escrever "format": "email" e achar que esta
        protegido e o erro que este teste existe pra impedir.
        """
        campos_tortos = [
            ("email", "isto-nao-e-um-email"),
            ("email", "sem-arroba.com"),
            ("email", "a@b"),
            ("email", "com espaco@exemplo.com"),
            ("email", "dois@@exemplo.com"),
            ("document_number", "12345678901"),
            ("document_number", "123.456.789-0"),
            ("document_number", "123-456-789.09"),
            ("document_number", "abc.def.ghi-jk"),
            ("birthdate", "17/05/1990"),
            ("birthdate", "1990-5-17"),
            ("birthdate", "19900517"),
            ("birthdate", "ontem"),
        ]

        for campo, valor_torto in campos_tortos:
            payload = PayloadGenerator.create_client_payload()
            payload[campo] = valor_torto

            status, response = RequestGenerator.POST_client(payload)

            assert status == 400, f"o campo '{campo}' aceitou o valor '{valor_torto}'"
            assert response["code"] == "QIT000001"

    @pytest.mark.parametrize("field", REQUIRED_FIELDS)
    @pytest.mark.parametrize("wrong_value", [None, 123, True, ["x"], {"a": 1}], ids=["null", "int", "bool", "list", "dict"])
    def test_refuses_wrong_types(self, field, wrong_value):
        payload = PayloadGenerator.create_client_payload()
        payload[field] = wrong_value

        status, response = RequestGenerator.POST_client(payload)

        assert status == 400, f"'{field}' aceitou {wrong_value!r}"
        assert response["code"] == "QIT000001"

    def test_refuses_a_body_that_is_not_a_json_object(self):
        for body in [[1, 2], "texto", 42]:
            status, response = RequestGenerator.POST_client(body)
            assert status == 400, f"aceitou o corpo {body!r}"
            assert response["code"] == "QIT000001"

    def test_refuses_body_that_is_not_json(self):
        response = RequestGenerator.send_raw(
            "POST", "/client",
            headers={**RequestGenerator.build_headers(), "Content-Type": "application/json"},
            data="isto nao e json",
        )
        assert response.response_status == 400
        assert response.response_json["code"] == "QIT000001"


class TestClientCreateBoundaries:
    """Analise de valor limite: o ultimo valor aceito e o primeiro recusado de cada campo."""

    def test_name_length_limits(self):
        status, _response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(name="A"))
        assert status == 201, "nome com 1 caractere deveria passar"

        status, _response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(name="A" * 255))
        assert status == 201, "nome com 255 caracteres deveria passar"

        for invalid in ["", "A" * 256]:
            status, response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(name=invalid))
            assert status == 400, f"nome com {len(invalid)} caracteres passou"
            assert response["code"] == "QIT000001"

    def test_password_length_limits(self):
        for valid in ["12345678", "a" * 255]:
            status, _response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(password=valid))
            assert status == 201, f"senha com {len(valid)} caracteres deveria passar"

        for invalid in ["1234567", "", "a" * 256]:
            status, response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(password=invalid))
            assert status == 400, f"senha com {len(invalid)} caracteres passou"
            assert response["code"] == "QIT000001"

    def test_email_length_limit(self):
        domain = "@exemplo.com.br"
        valid_email = ("a" * (255 - len(domain) - 36)) + str(uuid4()) + domain
        assert len(valid_email) == 255
        status, _response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(email=valid_email))
        assert status == 201, "e-mail com 255 caracteres deveria passar"

        status, response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(email="b" + valid_email))
        assert status == 400, "e-mail com 256 caracteres passou"
        assert response["code"] == "QIT000001"

    def test_accepts_exactly_eighteen_years_today(self):
        """Faz 18 anos hoje: a idade minima ja vale (limite aceito)."""
        payload = PayloadGenerator.create_client_payload(birthdate=PayloadGenerator.birthdate_turning_18_today())

        status, _response = RequestGenerator.POST_client(payload)

        assert status == 201

    def test_refuses_who_turns_eighteen_tomorrow(self):
        """Faz 18 anos amanha: um dia de diferenca decide (limite recusado)."""
        payload = PayloadGenerator.create_client_payload(birthdate=PayloadGenerator.birthdate_turning_18_tomorrow())

        status, response = RequestGenerator.POST_client(payload)

        assert status == 422
        assert response["code"] == "QIT001006"

    def test_refuses_a_birthdate_in_the_future(self):
        payload = PayloadGenerator.create_client_payload(birthdate=PayloadGenerator.birthdate_in_the_future())

        status, response = RequestGenerator.POST_client(payload)

        assert status == 422
        assert response["code"] in ("QIT001006", "QIT001007")

    def test_accepts_a_very_old_client(self):
        """Nao existe idade maxima: quem tem 90 anos e cadastrado normalmente."""
        payload = PayloadGenerator.create_client_payload(birthdate="1930-01-01")

        status, _response = RequestGenerator.POST_client(payload)

        assert status == 201

    def test_refuses_impossible_birthdate(self):
        """Formato certo, data inexistente: 422, nunca 500.

        O `pattern` do schema conta digitos; ele nao sabe que fevereiro
        nao tem dia 30. Estas datas passam pelo regex inteiras, e quem as
        recusa e o controller.
        """
        for impossible_birthdate in ["9999-99-99", "2025-02-30", "2023-02-29", "2000-13-01", "2000-00-10", "0000-01-01"]:
            payload = PayloadGenerator.create_client_payload()
            payload["birthdate"] = impossible_birthdate

            status, response = RequestGenerator.POST_client(payload)
            assert status == 422, f"{impossible_birthdate} nao deveria existir"
            assert response["code"] == "QIT001007"

    def test_accepts_29_february_of_a_leap_year(self):
        payload = PayloadGenerator.create_client_payload(birthdate="2000-02-29")

        status, _response = RequestGenerator.POST_client(payload)

        assert status == 201


class TestClientCreateBusinessRules:
    def test_refuses_invalid_document_number(self):
        """CPF com a mascara certa e os digitos errados nao passa.

        O schema ja cobrou o FORMATO (tres pontos, um hifen, onze
        digitos). Esta regra e outra: os dois ultimos digitos sao uma
        conta feita sobre os nove primeiros, e um numero que erra essa
        conta nao existe como CPF. Formato certo e valor impossivel — por
        isso a resposta e 422, e nao 400.
        """
        for invalid in ["111.222.333-44", "111.111.111-11", "000.000.000-00", "123.456.789-00"]:
            payload = PayloadGenerator.create_client_payload()
            payload["document_number"] = invalid

            status, response = RequestGenerator.POST_client(payload)

            assert status == 422, f"o CPF {invalid} nao existe e foi aceito"
            assert response["code"] == "QIT001003"

    def test_accepts_a_known_valid_cpf(self):
        """O CPF de teste conhecido (nao pertence a ninguem) passa na conta dos digitos."""
        payload = PayloadGenerator.create_client_payload(document_number="529.982.247-25")

        status, response = RequestGenerator.POST_client(payload)

        # 409 tambem e prova de que o CPF foi aceito como valido numa rodada anterior
        assert status in (201, 409)
        if status == 409:
            assert response["code"] == "QIT001004"

    def test_refuses_duplicated_document_number(self):
        primeira = PayloadGenerator.create_client_payload()
        status, _response = RequestGenerator.POST_client(primeira)
        assert status == 201

        segunda = PayloadGenerator.create_client_payload()
        segunda["document_number"] = primeira["document_number"]

        status, response = RequestGenerator.POST_client(segunda)

        assert status == 409
        assert response["code"] == "QIT001004"

    def test_refuses_duplicated_email(self):
        primeira = PayloadGenerator.create_client_payload()
        status, _response = RequestGenerator.POST_client(primeira)
        assert status == 201

        segunda = PayloadGenerator.create_client_payload()
        segunda["email"] = primeira["email"]

        status, response = RequestGenerator.POST_client(segunda)

        assert status == 409
        assert response["code"] == "QIT001005"

    @known_bug("BUG-EMAIL-CASE", "e-mails que so diferem na caixa viram dois cadastros (regra a confirmar com o time)")
    def test_refuses_duplicated_email_ignoring_case(self):
        base = f"Pessoa.{uuid4().hex[:10]}@Exemplo.com.br"
        status, _response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(email=base))
        assert status == 201

        status, response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(email=base.lower()))

        assert status == 409
        assert response["code"] == "QIT001005"

    def test_a_refused_signup_leaves_nothing_behind(self, operator_token):
        """Recusa nao pode deixar meia entidade no banco.

        Cada tentativa abaixo e recusada por um motivo diferente; depois,
        o CPF de cada uma NAO pode ter virado cliente.
        """
        existing = ObjectGenerator.create_client()
        attempts = [
            PayloadGenerator.create_client_payload(birthdate=PayloadGenerator.birthdate_turning_18_tomorrow()),
            PayloadGenerator.create_client_payload(document_number="111.222.333-44"),
            PayloadGenerator.create_client_payload(birthdate="2025-02-30"),
            PayloadGenerator.create_client_payload(email=existing["email"]),
        ]

        for payload in attempts:
            status, _response = RequestGenerator.POST_client(payload)
            assert status in (409, 422)

            status, response = RequestGenerator.GET_clients(operator_token, {"document_number": payload["document_number"]})
            assert status == 200
            assert response["data"] == [], f"a tentativa recusada deixou o CPF {payload['document_number']} cadastrado"

    def test_creates_client_approved_with_an_account(self):
        """Cadastro normal: o KYC e o antifraude aprovam e o cliente ja nasce aprovado, com conta.

        A trilha mostra a historia inteira: pending (criacao) -> approved.
        """
        client, jwt_token = ObjectGenerator.create_authenticated_client()
        _key = client["client_key"]

        status, response = RequestGenerator.GET_client(_key, jwt_token)
        assert status == 200
        assert response["client_key"] == _key
        assert response["name"] == client["name"]
        assert response["email"] == client["email"]
        assert response["document_number"] == client["document_number"]
        assert response["birthdate"] == client["birthdate"]
        assert response["status"] == "approved"

        assert len(response["accounts"]) == 1
        account = response["accounts"][0]
        assert account["account_key"]
        assert account["balance"] == "0.00"
        assert account["status"] == "active"

    def test_creates_client_rejected_when_kyc_refuses(self):
        """O KYC recusa a identidade (CPF com '99' no mock): o pedido NAO falha, o cliente nasce `rejected`.

        E o mesmo desenho do "passar dos limites nao e erro, e outro
        desfecho": 201, mas sem conta aberta.
        """
        client = ObjectGenerator.create_rejected_client()
        token = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]

        status, response = RequestGenerator.GET_client(client["client_key"], token)

        assert status == 200
        assert response["status"] == "rejected"
        assert response["accounts"] == []

    def test_post_returns_only_the_client_key(self):
        status, response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload())

        assert status == 201
        assert list(response.keys()) == ["client_key"]

    def test_signup_needs_no_login(self):
        """O cadastro e a unica rota de negocio aberta a quem ainda nao tem conta: sem Bearer."""
        status, _response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload())

        assert status == 201

    def test_signup_still_needs_the_internal_token(self):
        status, response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(), internal_token=None)

        assert status == 403
        assert response["code"] == "QIT000002"

    def test_password_is_never_returned(self):
        client, token = ObjectGenerator.create_authenticated_client()

        status, response = RequestGenerator.GET_client(client["client_key"], token)

        assert status == 200
        assert "password" not in response
        assert "password_hash" not in response
        assert client["password"] not in str(response)

    def test_accents_and_symbols_in_the_name_survive_a_round_trip(self):
        name = "José da Conceição D'Ávila-Öztürk"
        client = ObjectGenerator.create_client(name=name)
        token = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]

        status, response = RequestGenerator.GET_client(client["client_key"], token)

        assert status == 200
        assert response["name"] == name

    def test_sql_injection_in_the_name_is_stored_as_plain_text(self):
        name = "Robert'); DROP TABLE client;--"
        client = ObjectGenerator.create_client(name=name)
        token = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]

        status, response = RequestGenerator.GET_client(client["client_key"], token)

        assert status == 200
        assert response["name"] == name

    def test_accepts_plus_addressing_and_subdomains_in_the_email(self):
        email = f"pessoa+teste.{uuid4().hex[:8]}@mail.exemplo.com.br"

        status, _response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload(email=email))

        assert status == 201

    def test_same_name_and_birthdate_are_allowed_for_different_people(self):
        """Homonimos existem: so CPF e e-mail sao unicos."""
        for _ in range(2):
            status, _response = RequestGenerator.POST_client(
                PayloadGenerator.create_client_payload(name="Joao Silva", birthdate="1985-03-03")
            )
            assert status == 201

    @known_bug(
        "BUG-RACE-SIGNUP",
        "cadastros simultaneos com o mesmo CPF devolvem 500 em vez de 409 (a checagem de duplicidade nao e atomica)",
    )
    def test_simultaneous_signups_with_the_same_document_create_only_one(self):
        document_number = RandomGenerator.generate_cpf()

        def signup(_):
            payload = PayloadGenerator.create_client_payload(document_number=document_number)
            status, _response = RequestGenerator.POST_client(payload)
            return status

        with ThreadPoolExecutor(max_workers=6) as pool:
            statuses = list(pool.map(signup, range(6)))

        assert statuses.count(201) == 1, statuses
        assert set(statuses) <= {201, 409}, f"esperava so 201 e 409, veio {sorted(statuses)}"
