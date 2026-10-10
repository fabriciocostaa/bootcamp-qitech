from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from tests.utils import ObjectGenerator, RequestGenerator


def credit_withdraw(client, amount, key=None, client_key=None, token=None):
    return RequestGenerator.POST_credit_withdraw(
        client_key or client["client_key"], token or client["token"], key or str(uuid4()), amount
    )


def client_with_credit() -> tuple:
    client = ObjectGenerator.create_active_client()
    line = ObjectGenerator.open_credit_line(client)
    return client, line["limit_cents"]


class TestCreditWithdraw:
    """Saque do limite: o dinheiro entra na conta e a divida (com juros de 2%) vai pra fatura."""

    def test_withdraw_credits_the_account_and_opens_the_invoice(self):
        client, limit = client_with_credit()

        status, response = credit_withdraw(client, 10000)

        assert status == 201
        assert response["status"] == "APPROVED"
        assert response["withdrawn_amount"] == 10000
        assert response["fee_charged"] == 200
        assert response["total_cost"] == 10200
        assert response["invoice_amount_due"] == 10200
        assert response["remaining_credit_limit"] == limit - 10200
        assert response["new_account_balance"] == 10000
        assert ObjectGenerator.get_balance(client) == 10000

    def test_successive_withdrawals_accumulate_the_invoice(self):
        client, limit = client_with_credit()

        credit_withdraw(client, 10000)
        status, response = credit_withdraw(client, 5000)

        assert status == 201
        assert response["invoice_amount_due"] == 10200 + 5100
        assert response["remaining_credit_limit"] == limit - 10200 - 5100
        assert response["new_account_balance"] == 15000

    def test_integral_json_number_keeps_the_two_percent_fee(self):
        client, limit = client_with_credit()

        status, response = credit_withdraw(client, 1000.0)

        assert status == 201
        assert response["fee_charged"] == 20
        assert response["invoice_amount_due"] == 1020
        assert response["remaining_credit_limit"] == limit - 1020
        assert ObjectGenerator.get_balance(client) == 1000

    def test_credit_money_is_spendable(self):
        client, _limit = client_with_credit()
        credit_withdraw(client, 10000)

        status, _response = RequestGenerator.POST_account_withdraw(
            client["account_key"], client["token"], str(uuid4()), 10000
        )

        assert status == 200
        assert ObjectGenerator.get_balance(client) == 0

    def test_amount_that_still_fits_in_the_limit_is_approved(self):
        client, limit = client_with_credit()
        amount = (limit * 50 // 51) // 50 * 50  # maior multiplo de 50 cujo custo (valor + 2%) cabe no limite

        status, response = credit_withdraw(client, amount)

        assert status == 201
        assert response["remaining_credit_limit"] >= 0

    def test_amount_that_just_exceeds_the_limit_is_rejected(self):
        client, limit = client_with_credit()
        amount = (limit * 50 // 51) // 50 * 50 + 100

        status, response = credit_withdraw(client, amount)

        assert status == 422
        assert response["status"] == "REJECTED"
        assert ObjectGenerator.get_balance(client) == 0

    def test_second_withdrawal_beyond_what_is_left_is_rejected(self):
        client, limit = client_with_credit()
        first = (limit // 2) // 50 * 50
        assert credit_withdraw(client, first)[0] == 201

        status, response = credit_withdraw(client, first)

        assert status == 422
        assert response["status"] == "REJECTED"
        assert ObjectGenerator.get_balance(client) == first

    def test_without_a_credit_line_it_is_rejected(self):
        client = ObjectGenerator.create_active_client()

        status, response = credit_withdraw(client, 1000)

        assert status == 422
        assert response["status"] == "REJECTED"
        assert ObjectGenerator.get_balance(client) == 0

    def test_unknown_client(self):
        client = ObjectGenerator.create_active_client()

        status, response = credit_withdraw(client, 1000, client_key=str(uuid4()))

        assert status == 404
        assert response["code"] == "QIT001001"

    def test_missing_idempotency_key(self):
        client, _limit = client_with_credit()

        status, response = RequestGenerator.POST_credit_withdraw(client["client_key"], client["token"], None, 1000)

        assert status == 400
        assert response["code"] == "QIT003008"

    def test_requires_authentication(self):
        client, _limit = client_with_credit()

        status, response = RequestGenerator.POST_credit_withdraw(client["client_key"], None, str(uuid4()), 1000)

        assert status == 401
        assert response["code"] == "QIT003002"

    @pytest.mark.parametrize("amount", [0, -1, 10.5, "100", None, True], ids=lambda v: repr(v))
    def test_refuses_invalid_amount(self, amount):
        client, _limit = client_with_credit()

        status, response = credit_withdraw(client, amount)

        assert status == 400, f"aceitou amount={amount!r}"
        assert response["code"] == "QIT000001"
        assert ObjectGenerator.get_balance(client) == 0

    def test_refuses_missing_amount_and_extra_fields(self):
        client, _limit = client_with_credit()
        headers = RequestGenerator.build_headers(client["token"], str(uuid4()))
        path = f"/client/{client['client_key']}/credit/withdraw"

        for body in [{}, {"amount": 100, "extra": 1}]:
            response = RequestGenerator.send_raw("POST", path, headers=headers, payload=body)
            assert response.response_status == 400, body
            assert response.response_json["code"] == "QIT000001"

    def test_cannot_withdraw_credit_of_another_client(self):
        victim, _limit = client_with_credit()
        intruder = ObjectGenerator.create_active_client()

        status, response = credit_withdraw(intruder, 1000, client_key=victim["client_key"])

        assert status == 401
        assert response["code"] == "QIT003005"
        assert ObjectGenerator.get_balance(victim) == 0

    def test_replay_with_the_same_key_withdraws_once(self):
        client, _limit = client_with_credit()
        key = str(uuid4())
        first_status, _first = credit_withdraw(client, 10000, key=key)

        status, _response = credit_withdraw(client, 10000, key=key)

        assert first_status == 201
        assert status in (200, 201)
        assert ObjectGenerator.get_balance(client) == 10000

    def test_same_key_with_a_different_amount_is_a_conflict(self):
        client, _limit = client_with_credit()
        key = str(uuid4())
        assert credit_withdraw(client, 10000, key=key)[0] == 201

        status, response = credit_withdraw(client, 5000, key=key)

        assert status == 409
        assert response["code"] == "QIT003007"
        assert ObjectGenerator.get_balance(client) == 10000

    def test_account_deposit_key_cannot_be_reused_for_credit_withdrawal(self):
        client, _limit = client_with_credit()
        key = str(uuid4())
        assert RequestGenerator.POST_account_deposit(client["account_key"], client["token"], key, 4000)[0] == 200

        status, response = credit_withdraw(client, 4000, key=key)

        assert status == 409
        assert response["code"] == "QIT003007"
        assert ObjectGenerator.get_balance(client) == 4000

    def test_simultaneous_same_key_withdrawals_credit_once(self):
        client, limit = client_with_credit()
        key = str(uuid4())
        ready = Barrier(2)

        def withdraw():
            ready.wait(timeout=10)
            return credit_withdraw(client, 10000, key=key)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(withdraw) for _ in range(2)]
            results = [future.result(timeout=30) for future in futures]

        assert [status for status, _response in results] == [201, 201]
        for _status, response in results:
            assert response["withdrawn_amount"] == 10000
            assert response["fee_charged"] == 200
            assert response["invoice_amount_due"] == 10200
            assert response["remaining_credit_limit"] == limit - 10200
        assert ObjectGenerator.get_balance(client) == 10000

        status, response = credit_withdraw(client, 1000)

        assert status == 201
        assert response["invoice_amount_due"] == 11220
        assert response["remaining_credit_limit"] == limit - 11220
        assert ObjectGenerator.get_balance(client) == 11000
