from datetime import datetime
from uuid import uuid4

import jwt
import pytest

from tests.utils import ObjectGenerator, RequestGenerator


class TestStatusHistory:
    @pytest.mark.parametrize("resource, expected_statuses", [
        ("client", ["pending", "approved"]),
        ("account", ["active"]),
    ])
    def test_operator_reads_the_initial_history(self, operator_token, resource, expected_statuses):
        client = ObjectGenerator.create_active_client()
        response = RequestGenerator.send_raw(
            "GET", f"/{resource}/{client[f'{resource}_key']}/status-events",
            headers=RequestGenerator.build_headers(jwt_token=operator_token),
        )

        assert response.response_status == 200
        assert set(response.response_json) == {"status_events"}
        events = response.response_json["status_events"]
        assert [event["status"] for event in events] == expected_statuses
        assert all(set(event) == {"status", "event_datetime", "operator_key"} for event in events)
        assert all(event["operator_key"] is None for event in events)
        times = [datetime.fromisoformat(event["event_datetime"]) for event in events]
        assert times == sorted(times)

    def test_client_approval_records_the_operator(self, operator_token):
        client = ObjectGenerator.create_rejected_client()
        ObjectGenerator.update_client(client["client_key"], "approved", operator_token)

        response = RequestGenerator.send_raw(
            "GET", f"/client/{client['client_key']}/status-events",
            headers=RequestGenerator.build_headers(jwt_token=operator_token),
        )

        assert response.response_status == 200
        events = response.response_json["status_events"]
        assert [event["status"] for event in events] == ["pending", "rejected", "approved"]
        operator_key = jwt.decode(operator_token, options={"verify_signature": False})["subject_key"]
        assert [event["operator_key"] for event in events] == [None, None, operator_key]
        times = [datetime.fromisoformat(event["event_datetime"]) for event in events]
        assert times == sorted(times)

    def test_account_status_changes_record_the_operator(self, operator_token):
        client = ObjectGenerator.create_active_client()
        headers = RequestGenerator.build_headers(jwt_token=operator_token)
        for status in ["blocked", "active"]:
            response = RequestGenerator.send_raw(
                "PATCH", f"/account/{client['account_key']}",
                headers=headers, payload={"status": status},
            )
            assert response.response_status == 202
            assert response.response_json == {"account_key": client["account_key"]}

        response = RequestGenerator.send_raw(
            "GET", f"/account/{client['account_key']}/status-events", headers=headers,
        )

        assert response.response_status == 200
        events = response.response_json["status_events"]
        assert [event["status"] for event in events] == ["active", "blocked", "active"]
        operator_key = jwt.decode(operator_token, options={"verify_signature": False})["subject_key"]
        assert [event["operator_key"] for event in events] == [None, operator_key, operator_key]
        times = [datetime.fromisoformat(event["event_datetime"]) for event in events]
        assert times == sorted(times)

    @pytest.mark.parametrize("resource", ["client", "account"])
    @pytest.mark.parametrize("reader", ["owner", "another_client"])
    def test_client_cannot_read_operator_history(self, resource, reader):
        owner = ObjectGenerator.create_active_client()
        token = owner["token"] if reader == "owner" else ObjectGenerator.create_active_client()["token"]

        response = RequestGenerator.send_raw(
            "GET", f"/{resource}/{owner[f'{resource}_key']}/status-events",
            headers=RequestGenerator.build_headers(jwt_token=token),
        )

        assert response.response_status == 403
        assert response.response_json["code"] == "QIT003006"
        assert "status_events" not in response.response_json

    @pytest.mark.parametrize("resource", ["client", "account"])
    def test_history_requires_authentication(self, resource):
        client = ObjectGenerator.create_active_client()
        response = RequestGenerator.send_raw(
            "GET", f"/{resource}/{client[f'{resource}_key']}/status-events",
            headers=RequestGenerator.build_headers(),
        )

        assert response.response_status == 401
        assert response.response_json["code"] == "QIT003002"

    @pytest.mark.parametrize("resource, error_code", [
        ("client", "QIT001001"), ("account", "QIT002001"),
    ])
    def test_operator_gets_not_found_for_unknown_history(self, operator_token, resource, error_code):
        response = RequestGenerator.send_raw(
            "GET", f"/{resource}/{uuid4()}/status-events",
            headers=RequestGenerator.build_headers(jwt_token=operator_token),
        )

        assert response.response_status == 404
        assert response.response_json["code"] == error_code
