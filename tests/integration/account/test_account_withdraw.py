from uuid import uuid4

from tests.utils import ObjectGenerator, RequestGenerator


def withdraw(client, amount, key=None, account_key=None, token=None):
    return RequestGenerator.POST_account_withdraw(
        account_key or client["account_key"], token or client["token"], key or str(uuid4()), amount
    )


class TestWithdraw:
    def test_withdraw_debits_the_account(self):
        client = ObjectGenerator.create_active_client(balance=5000)

        status, response = withdraw(client, 1200)

        assert status == 200
        assert sorted(response.keys()) == ["amount", "created_at", "fee", "kind", "operation_key"]
        assert response["kind"] == "withdraw"
        assert response["amount"] == "12.00"
        assert response["fee"] == "0.00"
        assert ObjectGenerator.get_balance(client) == 3800

    def test_withdraw_exactly_the_whole_balance(self):
        """Valor limite: sacar TUDO e permitido e deixa zero (nao negativo, nao recusado)."""
        client = ObjectGenerator.create_active_client(balance=2500)

        status, _response = withdraw(client, 2500)

        assert status == 200
        assert ObjectGenerator.get_balance(client) == 0

    def test_withdraw_one_cent_more_than_the_balance_is_refused(self):
        """Valor limite: saldo + 1 centavo. O saldo nao muda."""
        client = ObjectGenerator.create_active_client(balance=2500)

        status, response = withdraw(client, 2501)

        assert status == 422
        assert response["code"] == "QIT002003"
        assert ObjectGenerator.get_balance(client) == 2500

    def test_withdraw_from_an_empty_account_is_refused(self):
        client = ObjectGenerator.create_active_client()

        status, response = withdraw(client, 1)

        assert status == 422
        assert response["code"] == "QIT002003"
        assert ObjectGenerator.get_balance(client) == 0

    def test_successive_withdrawals_stop_when_the_money_ends(self):
        client = ObjectGenerator.create_active_client(balance=1000)

        assert withdraw(client, 400)[0] == 200
        assert withdraw(client, 400)[0] == 200
        status, response = withdraw(client, 400)

        assert status == 422
        assert response["code"] == "QIT002003"
        assert ObjectGenerator.get_balance(client) == 200

    def test_cannot_withdraw_from_another_clients_account(self):
        owner = ObjectGenerator.create_active_client(balance=3000)
        intruder = ObjectGenerator.create_active_client(balance=3000)

        status, response = withdraw(intruder, 500, account_key=owner["account_key"])

        assert status == 401
        assert response["code"] == "QIT003005"
        assert ObjectGenerator.get_balance(owner) == 3000
        assert ObjectGenerator.get_balance(intruder) == 3000

    def test_unknown_account(self):
        client = ObjectGenerator.create_active_client(balance=100)

        status, response = withdraw(client, 10, account_key=str(uuid4()))

        assert status == 404
        assert response["code"] == "QIT002001"

    def test_missing_idempotency_key(self):
        client = ObjectGenerator.create_active_client(balance=1000)

        status, response = RequestGenerator.POST_account_withdraw(client["account_key"], client["token"], None, 100)

        assert status == 400
        assert response["code"] == "QIT003008"
        assert ObjectGenerator.get_balance(client) == 1000

    def test_requires_authentication(self):
        client = ObjectGenerator.create_active_client(balance=1000)

        status, response = RequestGenerator.POST_account_withdraw(client["account_key"], None, str(uuid4()), 100)

        assert status == 401
        assert response["code"] == "QIT003002"
        assert ObjectGenerator.get_balance(client) == 1000
