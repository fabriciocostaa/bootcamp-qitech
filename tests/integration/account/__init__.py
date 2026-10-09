from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

from tests.utils import ObjectGenerator, RequestGenerator
from tests.utils.markers import known_bug
from tests.utils.money import expected_transfer_fee


class TestIdempotency:
    """Repetir a MESMA requisicao (mesma Idempotency-Key) nao repete o efeito.

    E o que permite ao cliente tentar de novo depois de um timeout sem
    medo de cobrar duas vezes.
    """

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
        """Dois clientes podem usar a mesma chave sem esbarrar um no outro."""
        key = str(uuid4())
        first = ObjectGenerator.create_active_client()
        second = ObjectGenerator.create_active_client()

        status1, op1 = RequestGenerator.POST_account_deposit(first["account_key"], first["token"], key, 1000)
        status2, op2 = RequestGenerator.POST_account_deposit(second["account_key"], second["token"], key, 1000)

        assert (status1, status2) == (200, 200)
        assert op1["operation_key"] != op2["operation_key"]
        assert ObjectGenerator.get_balance(first) == 1000
        assert ObjectGenerator.get_balance(second) == 1000

    @known_bug("BUG-IDEM-CROSS-ENDPOINT", "a chave nao considera o tipo de operacao: reusar a chave de um deposito num saque do mesmo valor devolve o deposito e nao saca nada")
    def test_key_reused_for_a_different_operation_is_a_conflict(self):
        client = ObjectGenerator.create_active_client()
        key = str(uuid4())
        RequestGenerator.POST_account_deposit(client["account_key"], client["token"], key, 1000)

        status, _response = RequestGenerator.POST_account_withdraw(client["account_key"], client["token"], key, 1000)

        assert status == 409

    @known_bug("BUG-IDEM-EMPTY", "Idempotency-Key vazia e aceita; deveria ser 400")
    def test_empty_key_is_refused(self):
        client = ObjectGenerator.create_active_client()

        status, _response = RequestGenerator.POST_account_deposit(client["account_key"], client["token"], "", 100)

        assert status == 400

    @known_bug("BUG-IDEM-LONG", "Idempotency-Key com 300 caracteres estoura a coluna e devolve 500; deveria ser 400")
    def test_oversized_key_is_refused_not_a_500(self):
        client = ObjectGenerator.create_active_client()

        status, _response = RequestGenerator.POST_account_deposit(client["account_key"], client["token"], "k" * 300, 100)

        assert status == 400

    @known_bug("BUG-IDEM-RACE", "duas requisicoes simultaneas com a mesma chave: so uma vence e as outras recebem 500 em vez de repetir a resposta")
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


class TestConcurrency:
    def test_parallel_withdrawals_never_overdraw(self):
        """8 saques de TODO o saldo ao mesmo tempo: exatamente um passa, e o saldo termina em zero."""
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
        """A->B e B->A ao mesmo tempo: nenhum travamento e o dinheiro continua somando igual."""
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
