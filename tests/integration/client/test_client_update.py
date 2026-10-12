from uuid import uuid4

import pytest

from tests.utils import ObjectGenerator, PayloadGenerator, RequestGenerator


class TestClientUpdate:

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

        history = RequestGenerator.send_raw(
            "GET", f"/client/{_key}/status-events",
            headers=RequestGenerator.build_headers(jwt_token=operator_token),
        )
        assert history.response_status == 200
        assert [event["status"] for event in history.response_json["status_events"]] == ["pending", "rejected", "approved"]

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
        client = ObjectGenerator.create_rejected_client()
        _key = client["client_key"]

        history = RequestGenerator.send_raw(
            "GET", f"/client/{_key}/status-events",
            headers=RequestGenerator.build_headers(jwt_token=operator_token),
        )
        assert history.response_status == 200
        assert len(history.response_json["status_events"]) == 2

        ObjectGenerator.update_client(_key, "approved", operator_token)

        history = RequestGenerator.send_raw(
            "GET", f"/client/{_key}/status-events",
            headers=RequestGenerator.build_headers(jwt_token=operator_token),
        )
        assert history.response_status == 200
        trail = [event["status"] for event in history.response_json["status_events"]]
        times = [event["event_datetime"] for event in history.response_json["status_events"]]

        assert trail == ["pending", "rejected", "approved"]
        assert times == sorted(times), "a trilha precisa estar em ordem cronologica"

    def test_approved_client_cannot_change_status(self, operator_token):
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
        assert response["code"] == "QIT003001"
