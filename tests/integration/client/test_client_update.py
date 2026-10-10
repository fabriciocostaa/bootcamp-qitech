from uuid import uuid4

import pytest

from tests.utils import ObjectGenerator, PayloadGenerator, RequestGenerator


class TestClientUpdate:
    """PUT /client/{key} — so o OPERADOR muda status, e so de quem foi recusado (revisao manual)."""

    def test_operator_approves_a_rejected_client_and_an_account_is_opened(self, operator_token):
        client = ObjectGenerator.create_rejected_client()
        _key = client["client_key"]

        status, response = RequestGenerator.PUT_client(
            _key, operator_token, PayloadGenerator.create_new_status_payload("approved")
        )
        assert status == 202
        assert response["client_key"] == _key

        status, response = RequestGenerator.GET_client(_key, operator_token)
        assert status == 200
        assert response["name"] == client["name"]
        assert response["email"] == client["email"]
        assert response["document_number"] == client["document_number"]
        assert response["birthdate"] == client["birthdate"]
        assert response["status"] == "approved"

        # Cada mudanca de status deixa um evento: pending (criacao) + rejected (KYC) + approved (operador).
        assert [event["status"] for event in response["status_events"]] == ["pending", "rejected", "approved"]

        # Aprovar o cadastro cria uma conta com saldo zero.
        assert len(response["accounts"]) == 1
        account = response["accounts"][0]
        assert account["account_key"] is not None
        assert account["balance"] == "0.00"
        assert account["status"] == "active"

    def test_account_opened_by_manual_approval_is_usable(self, operator_token):
        client = ObjectGenerator.create_rejected_client()
        ObjectGenerator.update_client(client["client_key"], "approved", operator_token)
        client["token"] = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]
        _status, body = RequestGenerator.GET_client(client["client_key"], client["token"])
        client["account_key"] = body["accounts"][0]["account_key"]

        ObjectGenerator.deposit(client, 1500)

        assert ObjectGenerator.get_balance(client) == 1500

    def test_status_events_keep_the_trail_in_order(self, operator_token):
        """O GET por chave conta a HISTORIA, nao so o estado de agora."""
        client = ObjectGenerator.create_rejected_client()
        _key = client["client_key"]

        status, response = RequestGenerator.GET_client(_key, operator_token)
        assert status == 200
        assert len(response["status_events"]) == 2

        ObjectGenerator.update_client(_key, "approved", operator_token)

        status, response = RequestGenerator.GET_client(_key, operator_token)
        trail = [event["status"] for event in response["status_events"]]
        times = [event["event_datetime"] for event in response["status_events"]]

        assert trail == ["pending", "rejected", "approved"]
        assert times == sorted(times), "a trilha precisa estar em ordem cronologica"

    def test_approved_client_cannot_change_status(self, operator_token):
        """Quem ja foi aprovado nao muda mais — nem pra approved, nem pra rejected."""
        client = ObjectGenerator.create_client()
        _key = client["client_key"]

        for new_status in ["approved", "rejected"]:
            status, response = RequestGenerator.PUT_client(
                _key, operator_token, PayloadGenerator.create_new_status_payload(new_status)
            )
            assert status == 409, f"approved -> {new_status} foi aceito"
            assert response["code"] == "QIT001002"

        status, response = RequestGenerator.GET_client(_key, operator_token)
        assert response["status"] == "approved"
        assert len(response["accounts"]) == 1

    def test_approving_twice_does_not_open_two_accounts(self, operator_token):
        client = ObjectGenerator.create_rejected_client()
        ObjectGenerator.update_client(client["client_key"], "approved", operator_token)

        status, response = RequestGenerator.PUT_client(
            client["client_key"], operator_token, PayloadGenerator.create_new_status_payload("approved")
        )
        assert status == 409
        assert response["code"] == "QIT001002"

        _status, body = RequestGenerator.GET_client(client["client_key"], operator_token)
        assert len(body["accounts"]) == 1

    def test_unknown_client(self, operator_token):
        status, response = RequestGenerator.PUT_client(
            str(uuid4()), operator_token, PayloadGenerator.create_new_status_payload("approved")
        )

        assert status == 404
        assert response["code"] == "QIT001001"

    def test_schema_refuses_status_outside_the_enum(self, operator_token):
        """So os status que o schema lista (approved/rejected) sao aceitos.

        O "enum" do put_client.json e o contrato de entrada: um status
        inventado — ou `pending`, que nao se escolhe — nem chega na regra.
        """
        client = ObjectGenerator.create_rejected_client()

        for invalid in ["status_que_nao_existe", "pending", "failed", "APPROVED", "", None, 1]:
            status, response = RequestGenerator.PUT_client(
                client["client_key"], operator_token, PayloadGenerator.create_new_status_payload(invalid)
            )
            assert status == 400, f"aceitou o status {invalid!r}"
            assert response["code"] == "QIT000001"

    def test_schema_refuses_missing_status_and_extra_fields(self, operator_token):
        client = ObjectGenerator.create_rejected_client()

        for payload in [{}, {"status": "approved", "name": "Outro Nome"}]:
            status, response = RequestGenerator.PUT_client(client["client_key"], operator_token, payload)
            assert status == 400, payload
            assert response["code"] == "QIT000001"

    def test_client_cannot_change_status(self):
        """Nem o dono do cadastro: aprovar ou recusar e trabalho de operador."""
        client, token = ObjectGenerator.create_authenticated_client()

        status, response = RequestGenerator.PUT_client(
            client["client_key"], token, PayloadGenerator.create_new_status_payload("rejected")
        )

        assert status == 403
        assert response["code"] == "QIT003006"

    def test_a_rejected_client_cannot_approve_itself(self):
        client = ObjectGenerator.create_rejected_client()
        token = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]

        status, response = RequestGenerator.PUT_client(
            client["client_key"], token, PayloadGenerator.create_new_status_payload("approved")
        )

        assert status == 403
        assert response["code"] == "QIT003006"
        _status, body = RequestGenerator.GET_client(client["client_key"], token)
        assert body["status"] == "rejected"

    def test_requires_authentication(self):
        client = ObjectGenerator.create_rejected_client()

        status, response = RequestGenerator.PUT_client(
            client["client_key"], None, PayloadGenerator.create_new_status_payload("approved")
        )

        assert status == 401
        assert response["code"] == "QIT003002"
