from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from uuid import uuid4

import pytest

from tests.utils import ObjectGenerator, RequestGenerator


def pay(client, amount, key=None, client_key=None, token=None):
    return RequestGenerator.POST_invoice_pay(
        client_key or client["client_key"], token or client["token"], key or str(uuid4()), {"amount": amount}
    )


def client_in_debt(withdrawn: int = 10000, extra_balance: int = 0) -> tuple:
    """Cliente com credito aberto e uma fatura de withdrawn + 2%. Devolve (cliente, limite)."""
    client = ObjectGenerator.create_active_client()
    limit = ObjectGenerator.open_credit_line(client)["limit_cents"]
    status, _response = RequestGenerator.POST_credit_withdraw(
        client["client_key"], client["token"], str(uuid4()), withdrawn
    )
    assert status == 201
    if extra_balance:
        ObjectGenerator.deposit(client, extra_balance)
    return client, limit


class TestInvoicePay:
    def test_partial_payment_reduces_the_debt_and_restores_the_limit(self):
        client, limit = client_in_debt(withdrawn=10000)  # fatura = 10200, saldo = 10000

        status, response = pay(client, 3000)

        assert status == 200
        assert response["status"] == "APPROVED"
        assert response["paid_amount"] == 3000
        assert response["remaining_amount_due"] == 7200
        assert response["new_account_balance"] == 7000
        assert response["restored_credit_limit"] == limit - 10200 + 3000
        assert ObjectGenerator.get_balance(client) == 7000

    def test_paying_the_whole_invoice_restores_the_whole_limit(self):
        client, limit = client_in_debt(withdrawn=10000, extra_balance=5000)  # fatura 10200, saldo 15000

        status, response = pay(client, 10200)

        assert status == 200
        assert response["remaining_amount_due"] == 0
        assert response["restored_credit_limit"] == limit
        assert response["new_account_balance"] == 4800

    def test_overpayment_is_capped_at_what_is_owed(self):
        """Pagar MAIS do que se deve cobra so a divida: o excedente fica na conta."""
        client, _limit = client_in_debt(withdrawn=10000, extra_balance=5000)  # fatura 10200, saldo 15000

        status, response = pay(client, 12000)

        assert status == 200
        assert response["paid_amount"] == 10200
        assert response["remaining_amount_due"] == 0
        assert ObjectGenerator.get_balance(client) == 4800

    def test_insufficient_balance_is_rejected_and_nothing_changes(self):
        client, _limit = client_in_debt(withdrawn=10000)
        RequestGenerator.POST_account_withdraw(client["account_key"], client["token"], str(uuid4()), 9500)  # saldo = 500

        status, response = pay(client, 3000)

        assert status == 422
        assert response["status"] == "REJECTED"
        assert ObjectGenerator.get_balance(client) == 500

    def test_nothing_to_pay_is_rejected_and_the_balance_is_untouched(self):
        client = ObjectGenerator.create_active_client(balance=5000)
        ObjectGenerator.open_credit_line(client)

        status, response = pay(client, 1000)

        assert status == 422
        assert response["status"] == "REJECTED"
        assert ObjectGenerator.get_balance(client) == 5000

    def test_after_the_invoice_is_paid_nothing_is_owed(self):
        client, _limit = client_in_debt(withdrawn=10000, extra_balance=5000)
        assert pay(client, 10200)[0] == 200

        status, response = pay(client, 100)

        assert status == 422
        assert response["status"] == "REJECTED"
        assert ObjectGenerator.get_balance(client) == 4800

    def test_without_a_credit_line_it_is_rejected(self):
        client = ObjectGenerator.create_active_client(balance=5000)

        status, response = pay(client, 1000)

        assert status == 422
        assert response["status"] == "REJECTED"
        assert ObjectGenerator.get_balance(client) == 5000

    @pytest.mark.parametrize("amount", [0, -1, -5000], ids=lambda v: repr(v))
    def test_non_positive_amount_is_rejected(self, amount):
        client, _limit = client_in_debt(withdrawn=10000)

        status, response = pay(client, amount)

        assert status == 422
        assert response["status"] == "REJECTED"
        assert ObjectGenerator.get_balance(client) == 10000

    def test_fractional_amount_does_not_change_the_debt(self):
        client, _limit = client_in_debt(withdrawn=10000)

        status, _response = pay(client, 10.5)

        assert status in (400, 422)
        assert ObjectGenerator.get_balance(client) == 10000

    @pytest.mark.parametrize("amount", ["x", None], ids=lambda v: repr(v))
    def test_non_numeric_amount_is_a_400_not_a_500(self, amount):
        client, _limit = client_in_debt(withdrawn=10000)

        status, _response = pay(client, amount)

        assert status == 400

    def test_refuses_missing_body_and_non_object_body(self):
        client, _limit = client_in_debt(withdrawn=10000)
        headers = RequestGenerator.build_headers(client["token"], str(uuid4()))
        path = f"/client/{client['client_key']}/invoice/pay"

        for body in [None, [1], "texto"]:
            response = RequestGenerator.send_raw("POST", path, headers=headers, payload=body)
            assert response.response_status == 400, body
            assert response.response_json["code"] == "QIT000001"

    def test_missing_idempotency_key(self):
        client, _limit = client_in_debt(withdrawn=10000)

        status, response = RequestGenerator.POST_invoice_pay(client["client_key"], client["token"], None, {"amount": 100})

        assert status == 400
        assert response["code"] == "QIT003008"

    def test_unknown_client(self):
        client = ObjectGenerator.create_active_client()

        status, response = pay(client, 100, client_key=str(uuid4()))

        assert status == 404
        assert response["code"] == "QIT001001"

    def test_requires_authentication(self):
        client, _limit = client_in_debt(withdrawn=10000)

        status, response = RequestGenerator.POST_invoice_pay(client["client_key"], None, str(uuid4()), {"amount": 100})

        assert status == 401
        assert response["code"] == "QIT003002"

    def test_cannot_pay_another_clients_invoice(self):
        victim, _limit = client_in_debt(withdrawn=10000)
        intruder = ObjectGenerator.create_active_client()

        status, response = pay(intruder, 1000, client_key=victim["client_key"])

        assert status == 401
        assert response["code"] == "QIT003005"
        assert ObjectGenerator.get_balance(victim) == 10000

    def test_replay_with_the_same_key_pays_once(self):
        client, _limit = client_in_debt(withdrawn=10000)
        key = str(uuid4())
        first_status, _first = pay(client, 3000, key=key)

        status, _response = pay(client, 3000, key=key)

        assert first_status == 200
        assert status == 200
        assert ObjectGenerator.get_balance(client) == 7000

    def test_same_key_with_a_different_amount_is_a_conflict(self):
        client, _limit = client_in_debt()
        key = str(uuid4())
        assert pay(client, 3000, key=key)[0] == 200

        status, response = pay(client, 2000, key=key)

        assert status == 409
        assert response["code"] == "QIT003007"
        assert ObjectGenerator.get_balance(client) == 7000

    def test_integral_json_number_replays_the_same_payment_as_an_integer(self):
        client, limit = client_in_debt()
        key = str(uuid4())
        first_status, first_response = pay(client, 3000.0, key=key)

        status, response = pay(client, 3000, key=key)

        assert first_status == 200
        assert status == 200
        assert response["paid_amount"] == first_response["paid_amount"] == 3000
        assert response["remaining_amount_due"] == 7200
        assert response["restored_credit_limit"] == limit - 7200
        assert ObjectGenerator.get_balance(client) == 7000

    def test_credit_withdrawal_key_cannot_be_reused_for_invoice_payment(self):
        client = ObjectGenerator.create_active_client()
        ObjectGenerator.open_credit_line(client)
        key = str(uuid4())
        assert RequestGenerator.POST_credit_withdraw(client["client_key"], client["token"], key, 10000)[0] == 201

        status, response = pay(client, 10000, key=key)

        assert status == 409
        assert response["code"] == "QIT003007"
        assert ObjectGenerator.get_balance(client) == 10000

    def test_invoice_payment_key_cannot_be_reused_for_credit_withdrawal(self):
        client, _limit = client_in_debt()
        key = str(uuid4())
        assert pay(client, 3000, key=key)[0] == 200

        status, response = RequestGenerator.POST_credit_withdraw(client["client_key"], client["token"], key, 3000)

        assert status == 409
        assert response["code"] == "QIT003007"
        assert ObjectGenerator.get_balance(client) == 7000

    def test_overpayment_checks_balance_against_the_actual_debt(self):
        client, limit = client_in_debt(extra_balance=5000)

        status, response = pay(client, 100000)

        assert status == 200
        assert response["paid_amount"] == 10200
        assert response["remaining_amount_due"] == 0
        assert response["restored_credit_limit"] == limit
        assert ObjectGenerator.get_balance(client) == 4800

    def test_replay_of_a_capped_payment_succeeds_after_the_debt_is_zero(self):
        client, limit = client_in_debt(extra_balance=100000)
        key = str(uuid4())
        first_status, first_response = pay(client, 100000, key=key)

        status, response = pay(client, 100000, key=key)

        assert first_status == 200
        assert status == 200
        assert response["paid_amount"] == first_response["paid_amount"] == 10200
        assert response["remaining_amount_due"] == 0
        assert response["restored_credit_limit"] == limit
        assert ObjectGenerator.get_balance(client) == 99800

    def test_simultaneous_same_key_payments_debit_once(self):
        client, limit = client_in_debt()
        key = str(uuid4())
        ready = Barrier(2)

        def payment():
            ready.wait(timeout=10)
            return pay(client, 3000, key=key)

        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(payment) for _ in range(2)]
            results = [future.result(timeout=30) for future in futures]

        assert [status for status, _response in results] == [200, 200]
        for _status, response in results:
            assert response["paid_amount"] == 3000
            assert response["remaining_amount_due"] == 7200
            assert response["restored_credit_limit"] == limit - 7200
        assert ObjectGenerator.get_balance(client) == 7000

    @pytest.mark.parametrize("payload", [{}, {"amount": True}, {"amount": 100, "extra": 1}, {"amount": 9223372036854775808}], ids=["missing", "boolean", "extra", "overflow"])
    def test_invalid_payment_schema_does_not_change_the_balance(self, payload):
        client, _limit = client_in_debt()

        status, response = RequestGenerator.POST_invoice_pay(client["client_key"], client["token"], str(uuid4()), payload)

        assert status == 400
        assert response["code"] == "QIT000001"
        assert ObjectGenerator.get_balance(client) == 10000
