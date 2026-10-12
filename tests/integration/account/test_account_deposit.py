from uuid import uuid4

import pytest

from tests.utils import ObjectGenerator, RequestGenerator
from tests.utils.money import to_cents


def deposit(client, amount, key=None, token=None):
    return RequestGenerator.POST_account_deposit(
        client["account_key"], token or client["token"], key or str(uuid4()), amount
    )


class TestDeposit:
    def test_deposit_credits_the_account(self):
        client = ObjectGenerator.create_active_client()

        status, response = deposit(client, 5000)

        assert status == 200
        assert sorted(response.keys()) == ["amount", "created_at", "fee", "kind", "operation_key"]
        assert response["kind"] == "deposit"
        assert response["amount"] == "50.00"
        assert response["fee"] == "0.00"
        assert response["operation_key"]
        assert ObjectGenerator.get_balance(client) == 5000

    def test_smallest_amount_is_one_cent(self):
        client = ObjectGenerator.create_active_client()

        status, response = deposit(client, 1)

        assert status == 200
        assert response["amount"] == "0.01"
        assert ObjectGenerator.get_balance(client) == 1

    def test_deposits_accumulate(self):
        client = ObjectGenerator.create_active_client()

        for amount in [100, 250, 4000]:
            status, _response = deposit(client, amount)
            assert status == 200

        assert ObjectGenerator.get_balance(client) == 4350

    def test_large_amount_is_accepted(self):
        client = ObjectGenerator.create_active_client()

        status, _response = deposit(client, 10**12)

        assert status == 200
        assert ObjectGenerator.get_balance(client) == 10**12

    def test_absurdly_large_amount_is_refused_not_a_500(self):
        client = ObjectGenerator.create_active_client()

        status, _response = deposit(client, 2**63)

        assert status in (400, 422)
        assert ObjectGenerator.get_balance(client) == 0

    def test_missing_idempotency_key(self):
        client = ObjectGenerator.create_active_client()

        status, response = RequestGenerator.POST_account_deposit(client["account_key"], client["token"], None, 100)

        assert status == 400
        assert response["code"] == "QIT003008"
        assert ObjectGenerator.get_balance(client) == 0

    def test_unknown_account(self):
        client = ObjectGenerator.create_active_client()

        status, response = RequestGenerator.POST_account_deposit(str(uuid4()), client["token"], str(uuid4()), 100)

        assert status == 404
        assert response["code"] == "QIT002001"

    def test_requires_authentication(self):
        client = ObjectGenerator.create_active_client()

        status, response = RequestGenerator.POST_account_deposit(client["account_key"], None, str(uuid4()), 100)

        assert status == 401
        assert response["code"] == "QIT003001"
        assert ObjectGenerator.get_balance(client) == 0

    def test_operator_token_is_refused_cleanly(self, operator_token):
        client = ObjectGenerator.create_active_client()

        status, _response = RequestGenerator.POST_account_deposit(
            client["account_key"], operator_token, str(uuid4()), 100
        )

        assert status in (401, 403)

    def test_refuses_extra_fields_and_missing_amount(self):
        client = ObjectGenerator.create_active_client()
        headers = RequestGenerator.build_headers(client["token"], str(uuid4()))
        path = f"/account/{client['account_key']}/deposit"

        for body in [{}, {"amount": 100, "extra": 1}, {"valor": 100}]:
            response = RequestGenerator.send_raw("POST", path, headers=headers, payload=body)
            assert response.response_status == 400, body
            assert response.response_json["code"] == "QIT000001"

    def test_refuses_body_that_is_not_json(self):
        client = ObjectGenerator.create_active_client()
        headers = {**RequestGenerator.build_headers(client["token"], str(uuid4())), "Content-Type": "application/json"}

        response = RequestGenerator.send_raw(
            "POST", f"/account/{client['account_key']}/deposit", headers=headers, data="nao e json"
        )

        assert response.response_status == 400
        assert response.response_json["code"] == "QIT000001"


class TestAmountValidation:

    INVALID_AMOUNTS = [0, -1, -100, 10.5, 0.5, "100", "", None, True, [100], {"v": 1}]

    @pytest.mark.parametrize("amount", INVALID_AMOUNTS, ids=lambda v: repr(v))
    def test_deposit_refuses_invalid_amount(self, amount):
        client = ObjectGenerator.create_active_client()

        status, response = deposit(client, amount)

        assert status == 400, f"deposito aceitou amount={amount!r}"
        assert response["code"] == "QIT000001"
        assert ObjectGenerator.get_balance(client) == 0

    @pytest.mark.parametrize("amount", INVALID_AMOUNTS, ids=lambda v: repr(v))
    def test_withdraw_refuses_invalid_amount(self, amount):
        client = ObjectGenerator.create_active_client(balance=1000)

        status, response = RequestGenerator.POST_account_withdraw(
            client["account_key"], client["token"], str(uuid4()), amount
        )

        assert status == 400, f"saque aceitou amount={amount!r}"
        assert response["code"] == "QIT000001"
        assert ObjectGenerator.get_balance(client) == 1000

    @pytest.mark.parametrize("amount", [0, -1, "100", None, True], ids=lambda v: repr(v))
    def test_transfer_refuses_invalid_amount(self, amount):
        origin = ObjectGenerator.create_active_client(balance=1000)
        destination = ObjectGenerator.create_active_client()

        status, response = RequestGenerator.POST_account_transfer(
            origin["account_key"], destination["account_key"], origin["token"], str(uuid4()), amount
        )

        assert status == 400, f"transferencia aceitou amount={amount!r}"
        assert response["code"] == "QIT000001"
        assert ObjectGenerator.get_balance(origin) == 1000
