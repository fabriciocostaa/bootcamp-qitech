from datetime import date, timedelta
from uuid import uuid4

import pytest

from tests.utils import ObjectGenerator, RequestGenerator
from tests.utils.money import expected_transfer_fee


def extract(client, params=None, token=None, account_key=None):
    return RequestGenerator.GET_account_extract(
        account_key or client["account_key"], token or client["token"], params
    )


def server_today(client) -> date:
    """O 'hoje' do SERVIDOR, lido de uma operacao recem-criada (evita brigar com fuso/relogio)."""
    created_at = ObjectGenerator.deposit(client, 1)["created_at"]
    return date.fromisoformat(created_at[:10])


class TestExtractContent:
    def test_empty_account_has_an_empty_last_page(self):
        client = ObjectGenerator.create_active_client()

        status, response = extract(client)

        assert status == 200
        assert response["data"] == []
        assert response["is_last_page"] is True
        assert response["page"] == 0
        assert response["limit"] == 10

    def test_entry_shape(self):
        client = ObjectGenerator.create_active_client(balance=1000)

        _status, response = extract(client)

        assert sorted(response["data"][0].keys()) == [
            "account_from_key", "account_to_key", "amount", "created_at", "fee", "transaction_id", "type",
        ]

    def test_lists_every_kind_of_operation_newest_first(self):
        client = ObjectGenerator.create_active_client(balance=10000)
        other = ObjectGenerator.create_active_client()
        RequestGenerator.POST_account_withdraw(client["account_key"], client["token"], str(uuid4()), 700)
        RequestGenerator.POST_account_transfer(
            client["account_key"], other["account_key"], client["token"], str(uuid4()), 1000
        )

        status, response = extract(client)

        assert status == 200
        types = [entry["type"] for entry in response["data"]]
        assert types == ["transfer_out", "fee_debit", "withdraw", "deposit"] or types == ["fee_debit", "transfer_out", "withdraw", "deposit"]
        created = [entry["created_at"] for entry in response["data"]]
        assert created == sorted(created, reverse=True), "o extrato deve vir do mais novo pro mais antigo"

    def test_transfer_amounts_and_fee_in_the_statement(self):
        client = ObjectGenerator.create_active_client(balance=10000)
        other = ObjectGenerator.create_active_client()
        RequestGenerator.POST_account_transfer(
            client["account_key"], other["account_key"], client["token"], str(uuid4()), 1000
        )

        _status, response = extract(client)
        out = next(entry for entry in response["data"] if entry["type"] == "transfer_out")
        fee_debit = next(entry for entry in response["data"] if entry["type"] == "fee_debit")

        assert out["amount"] == "10.00"
        assert out["account_from_key"] == client["account_key"]
        assert out["account_to_key"] == other["account_key"]
        assert fee_debit["amount"] == f"{expected_transfer_fee(1000) / 100:.2f}"

    def test_recipient_sees_the_incoming_transfer(self):
        client = ObjectGenerator.create_active_client(balance=10000)
        other = ObjectGenerator.create_active_client()
        RequestGenerator.POST_account_transfer(
            client["account_key"], other["account_key"], client["token"], str(uuid4()), 1000
        )

        status, response = extract(other)

        assert status == 200
        assert [(entry["type"], entry["amount"]) for entry in response["data"]] == [("transfer_in", "10.00")]

    def test_refused_operations_leave_no_entry(self):
        client = ObjectGenerator.create_active_client(balance=500)
        RequestGenerator.POST_account_withdraw(client["account_key"], client["token"], str(uuid4()), 99999)

        _status, response = extract(client)

        assert [entry["type"] for entry in response["data"]] == ["deposit"]

    def test_does_not_leak_other_accounts_operations(self):
        client = ObjectGenerator.create_active_client(balance=500)
        ObjectGenerator.create_active_client(balance=777)

        _status, response = extract(client)

        assert [entry["amount"] for entry in response["data"]] == ["5.00"]


class TestExtractAccess:
    def test_cannot_read_another_clients_statement(self):
        owner = ObjectGenerator.create_active_client(balance=500)
        intruder = ObjectGenerator.create_active_client()

        status, response = extract(intruder, account_key=owner["account_key"])

        assert status == 401
        assert response["code"] == "QIT003005"
        assert "5.00" not in str(response)

    def test_unknown_account(self):
        client = ObjectGenerator.create_active_client()

        status, response = extract(client, account_key=str(uuid4()))

        assert status == 404
        assert response["code"] == "QIT002001"

    def test_requires_authentication(self):
        client = ObjectGenerator.create_active_client()

        status, response = RequestGenerator.GET_account_extract(client["account_key"], None)

        assert status == 401
        assert response["code"] == "QIT003002"


class TestExtractPagination:
    def fund_with_deposits(self, count):
        client = ObjectGenerator.create_active_client()
        for i in range(count):
            ObjectGenerator.deposit(client, 100 + i)  # valores distintos: da pra conferir a ordem
        return client

    def test_pages_do_not_overlap_or_skip(self):
        client = self.fund_with_deposits(5)

        amounts = []
        for page in range(3):
            status, response = extract(client, {"limit": 2, "page": page})
            assert status == 200
            amounts += [entry["amount"] for entry in response["data"]]
            assert response["is_last_page"] is (page == 2)

        assert amounts == ["1.04", "1.03", "1.02", "1.01", "1.00"]

    def test_exactly_full_page_is_the_last_one(self):
        client = self.fund_with_deposits(4)

        status, response = extract(client, {"limit": 4})

        assert status == 200
        assert len(response["data"]) == 4
        assert response["is_last_page"] is True

    def test_page_beyond_the_end_is_empty(self):
        client = self.fund_with_deposits(2)

        status, response = extract(client, {"limit": 10, "page": 9})

        assert status == 200
        assert response["data"] == []
        assert response["is_last_page"] is True

    def test_limit_boundaries(self):
        client = self.fund_with_deposits(1)
        for limit in [1, 100]:
            status, response = extract(client, {"limit": limit})
            assert status == 200, f"limit={limit}"
            assert response["limit"] == limit

        for invalid in [101, -1, "abc", 1.5]:
            status, response = extract(client, {"limit": invalid})
            assert status == 400, f"limit={invalid}"
            assert response["code"] == "QIT000001"

    def test_limit_zero_is_refused(self):
        client = self.fund_with_deposits(1)

        status, response = extract(client, {"limit": 0})

        assert status == 400

    def test_invalid_page_and_unknown_param(self):
        client = self.fund_with_deposits(1)
        for params in [{"page": -1}, {"page": "x"}, {"foo": 1}]:
            status, response = extract(client, params)
            assert status == 400, params
            assert response["code"] == "QIT000001"


class TestExtractDateFilters:
    def test_start_date_today_keeps_todays_entries(self):
        client = ObjectGenerator.create_active_client()
        today = server_today(client)

        status, response = extract(client, {"start_date": today.isoformat()})

        assert status == 200
        assert len(response["data"]) == 1

    def test_start_date_tomorrow_hides_todays_entries(self):
        client = ObjectGenerator.create_active_client()
        today = server_today(client)

        status, response = extract(client, {"start_date": (today + timedelta(days=1)).isoformat()})

        assert status == 200
        assert response["data"] == []

    def test_end_date_yesterday_hides_todays_entries(self):
        client = ObjectGenerator.create_active_client()
        today = server_today(client)

        status, response = extract(client, {"end_date": (today - timedelta(days=1)).isoformat()})

        assert status == 200
        assert response["data"] == []

    def test_end_date_today_includes_todays_entries(self):
        client = ObjectGenerator.create_active_client()
        today = server_today(client)

        status, response = extract(client, {"end_date": today.isoformat()})

        assert status == 200
        assert len(response["data"]) == 1

    def test_range_around_today_includes_todays_entries(self):
        client = ObjectGenerator.create_active_client()
        today = server_today(client)

        status, response = extract(
            client, {"start_date": today.isoformat(), "end_date": (today + timedelta(days=1)).isoformat()}
        )

        assert status == 200
        assert len(response["data"]) == 1

    def test_inverted_range_is_refused(self):
        client = ObjectGenerator.create_active_client()

        status, response = extract(client, {"start_date": "2030-01-02", "end_date": "2030-01-01"})

        assert status == 422
        assert response["code"] == "QIT002006"

    def test_malformed_date_is_refused_by_the_schema(self):
        client = ObjectGenerator.create_active_client()
        for bad in ["01/01/2025", "2025-1-1", "ontem", "20250101"]:
            for field in ["start_date", "end_date"]:
                status, response = extract(client, {field: bad})
                assert status == 400, f"{field}={bad}"
                assert response["code"] == "QIT000001"

    @pytest.mark.parametrize("field", ["start_date", "end_date"])
    def test_impossible_date_is_a_422_not_a_500(self, field):
        client = ObjectGenerator.create_active_client()

        status, response = extract(client, {field: "2025-02-30"})

        assert status == 422
