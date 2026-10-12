from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from tests.utils import ObjectGenerator, RequestGenerator
from tests.utils.money import expected_transfer_fee


class TestIdempotency:

    def test_deposit_replay_returns_the_same_operation_and_credits_once(self):
        client = ObjectGenerator.create_active_client()
        key = str(uuid4())

        status1, first = RequestGenerator.POST_account_deposit(client["account_key"], client["token"], key, 2000)
        status2, second = RequestGenerator.POST_account_deposit(client["account_key"], client["token"], key, 2000)

        assert (status1, status2) == (200, 200)
        assert first["operation_key"] == second["operation_key"]
        assert ObjectGenerator.get_balance(client) == 2000

    def test_withdraw_replay_debits_once(self):
        client = ObjectGenerator.create_active_client(balance=5000)
        key = str(uuid4())

        _s, first = RequestGenerator.POST_account_withdraw(client["account_key"], client["token"], key, 1000)
        _s, second = RequestGenerator.POST_account_withdraw(client["account_key"], client["token"], key, 1000)

        assert first["operation_key"] == second["operation_key"]
        assert ObjectGenerator.get_balance(client) == 4000

    def test_transfer_replay_moves_money_and_charges_the_fee_once(self):
        origin = ObjectGenerator.create_active_client(balance=10000)
        destination = ObjectGenerator.create_active_client()
        key = str(uuid4())
        args = (origin["account_key"], destination["account_key"], origin["token"], key, 1000)

        _s, first = RequestGenerator.POST_account_transfer(*args)
        _s, second = RequestGenerator.POST_account_transfer(*args)

        assert first["operation_key"] == second["operation_key"]
        assert ObjectGenerator.get_balance(origin) == 10000 - 1000 - expected_transfer_fee(1000)
        assert ObjectGenerator.get_balance(destination) == 1000

    def test_same_key_with_a_different_amount_is_a_conflict(self):
        client = ObjectGenerator.create_active_client()
        key = str(uuid4())
        RequestGenerator.POST_account_deposit(client["account_key"], client["token"], key, 2000)

        status, response = RequestGenerator.POST_account_deposit(client["account_key"], client["token"], key, 3000)

        assert status == 409
        assert response["code"] == "QIT003007"
        assert ObjectGenerator.get_balance(client) == 2000

    def test_different_keys_with_the_same_payload_are_two_operations(self):
        client = ObjectGenerator.create_active_client()

        for _ in range(2):
            status, _response = RequestGenerator.POST_account_deposit(
                client["account_key"], client["token"], str(uuid4()), 1000
            )
            assert status == 200

        assert ObjectGenerator.get_balance(client) == 2000

    def test_keys_are_scoped_per_client(self):
        key = str(uuid4())
        first = ObjectGenerator.create_active_client()
        second = ObjectGenerator.create_active_client()

        status1, op1 = RequestGenerator.POST_account_deposit(first["account_key"], first["token"], key, 1000)
        status2, op2 = RequestGenerator.POST_account_deposit(second["account_key"], second["token"], key, 1000)

        assert (status1, status2) == (200, 200)
        assert op1["operation_key"] != op2["operation_key"]
        assert ObjectGenerator.get_balance(first) == 1000
        assert ObjectGenerator.get_balance(second) == 1000

    def test_key_reused_for_a_different_operation_is_a_conflict(self):
        client = ObjectGenerator.create_active_client()
        key = str(uuid4())
        RequestGenerator.POST_account_deposit(client["account_key"], client["token"], key, 1000)

        status, _response = RequestGenerator.POST_account_withdraw(client["account_key"], client["token"], key, 1000)

        assert status == 409

    @pytest.mark.parametrize("operation", ["deposit", "withdraw", "transfer"])
    def test_empty_key_is_refused(self, operation):
        client = ObjectGenerator.create_active_client(balance=200)

        if operation == "transfer":
            destination = ObjectGenerator.create_active_client()
            status, _response = RequestGenerator.POST_account_transfer(
                client["account_key"], destination["account_key"], client["token"], "", 100
            )
            assert ObjectGenerator.get_balance(destination) == 0
        else:
            method = getattr(RequestGenerator, f"POST_account_{operation}")
            status, _response = method(client["account_key"], client["token"], "", 100)

        assert status == 400
        assert _response["code"] == "QIT003008"
        assert ObjectGenerator.get_balance(client) == 200

    @pytest.mark.parametrize("operation", ["deposit", "withdraw", "transfer"])
    def test_oversized_key_is_refused_not_a_500(self, operation):
        client = ObjectGenerator.create_active_client(balance=200)

        if operation == "transfer":
            destination = ObjectGenerator.create_active_client()
            status, _response = RequestGenerator.POST_account_transfer(
                client["account_key"], destination["account_key"], client["token"], "k" * 300, 100
            )
            assert ObjectGenerator.get_balance(destination) == 0
        else:
            method = getattr(RequestGenerator, f"POST_account_{operation}")
            status, _response = method(client["account_key"], client["token"], "k" * 300, 100)

        assert status == 400
        assert _response["code"] == "QIT000010"
        assert ObjectGenerator.get_balance(client) == 200

    def test_simultaneous_requests_with_the_same_key_credit_once(self):
        client = ObjectGenerator.create_active_client()
        key = str(uuid4())

        def call(_):
            return RequestGenerator.POST_account_deposit(client["account_key"], client["token"], key, 500)

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(call, range(8)))

        assert {status for status, _ in results} == {200}, sorted(status for status, _ in results)
        assert len({body["operation_key"] for _, body in results}) == 1
        assert ObjectGenerator.get_balance(client) == 500

    def test_simultaneous_withdrawals_with_the_same_key_debit_once(self):
        client = ObjectGenerator.create_active_client(balance=500)
        key = str(uuid4())

        def call(_):
            return RequestGenerator.POST_account_withdraw(client["account_key"], client["token"], key, 500)

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(call, range(8)))

        assert {status for status, _ in results} == {200}, sorted(status for status, _ in results)
        assert len({body["operation_key"] for _, body in results}) == 1
        assert ObjectGenerator.get_balance(client) == 0

    def test_simultaneous_transfers_with_the_same_key_charge_the_fee_once(self):
        origin = ObjectGenerator.create_active_client(balance=1020)
        destination = ObjectGenerator.create_active_client()
        key = str(uuid4())

        def call(_):
            return RequestGenerator.POST_account_transfer(
                origin["account_key"], destination["account_key"], origin["token"], key, 1000
            )

        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(call, range(8)))

        assert {status for status, _ in results} == {200}, sorted(status for status, _ in results)
        assert len({body["operation_key"] for _, body in results}) == 1
        assert {body["fee"] for _, body in results} == {"0.20"}
        assert ObjectGenerator.get_balance(origin) == 0
        assert ObjectGenerator.get_balance(destination) == 1000


class TestConcurrency:
    def test_parallel_withdrawals_never_overdraw(self):
        client = ObjectGenerator.create_active_client(balance=1000)

        def call(_):
            status, _body = RequestGenerator.POST_account_withdraw(
                client["account_key"], client["token"], str(uuid4()), 1000
            )
            return status

        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(call, range(8)))

        assert statuses.count(200) == 1, sorted(statuses)
        assert statuses.count(422) == 7, sorted(statuses)
        assert ObjectGenerator.get_balance(client) == 0

    def test_parallel_transfers_never_overdraw(self):
        amount = 1000
        funds = amount + expected_transfer_fee(amount)
        origin = ObjectGenerator.create_active_client(balance=funds)
        destination = ObjectGenerator.create_active_client()

        def call(_):
            status, _body = RequestGenerator.POST_account_transfer(
                origin["account_key"], destination["account_key"], origin["token"], str(uuid4()), amount
            )
            return status

        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(call, range(8)))

        assert statuses.count(200) == 1, sorted(statuses)
        assert ObjectGenerator.get_balance(origin) == 0
        assert ObjectGenerator.get_balance(destination) == amount

    def test_parallel_deposits_with_different_keys_are_all_applied(self):
        client = ObjectGenerator.create_active_client()

        def call(_):
            status, _body = RequestGenerator.POST_account_deposit(
                client["account_key"], client["token"], str(uuid4()), 100
            )
            return status

        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(call, range(8)))

        assert set(statuses) == {200}
        assert ObjectGenerator.get_balance(client) == 800

    def test_crossed_transfers_do_not_deadlock(self):
        a = ObjectGenerator.create_active_client(balance=100000)
        b = ObjectGenerator.create_active_client(balance=100000)

        def call(i):
            src, dst = (a, b) if i % 2 == 0 else (b, a)
            status, _body = RequestGenerator.POST_account_transfer(
                src["account_key"], dst["account_key"], src["token"], str(uuid4()), 1000
            )
            return status

        with ThreadPoolExecutor(max_workers=8) as pool:
            statuses = list(pool.map(call, range(16)))

        assert set(statuses) == {200}, sorted(statuses)
        fee = expected_transfer_fee(1000)
        assert ObjectGenerator.get_balance(a) + ObjectGenerator.get_balance(b) == 200000 - 16 * fee
