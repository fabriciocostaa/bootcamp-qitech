from uuid import uuid4

import pytest

from tests.utils import ObjectGenerator, RequestGenerator


def test_deposit_on_another_clients_account_is_refused_without_changing_balances():
    owner = ObjectGenerator.create_active_client()
    intruder = ObjectGenerator.create_active_client()

    status, response = RequestGenerator.POST_account_deposit(
        owner["account_key"], intruder["token"], str(uuid4()), 100
    )

    assert status == 401
    assert response["code"] == "QIT003005"
    assert ObjectGenerator.get_balance(owner) == ObjectGenerator.get_balance(intruder) == 0


@pytest.mark.parametrize("operation", ["deposit", "withdraw", "transfer"])
def test_operator_cannot_execute_client_transactions(operator_token, operation):
    client = ObjectGenerator.create_active_client(balance=1000)
    target = ObjectGenerator.create_active_client()
    if operation == "transfer":
        status, response = RequestGenerator.POST_account_transfer(
            client["account_key"], target["account_key"], operator_token, str(uuid4()), 100
        )
    else:
        method = getattr(RequestGenerator, f"POST_account_{operation}")
        status, response = method(client["account_key"], operator_token, str(uuid4()), 100)

    assert status == 401
    assert response["code"] == "QIT003005"
    assert ObjectGenerator.get_balance(client) == 1000
    assert ObjectGenerator.get_balance(target) == 0


@pytest.mark.parametrize("operation", ["withdraw", "transfer"])
def test_amount_above_bigint_is_a_schema_error_without_changing_balances(operation):
    client = ObjectGenerator.create_active_client(balance=1000)
    target = ObjectGenerator.create_active_client()
    if operation == "transfer":
        status, response = RequestGenerator.POST_account_transfer(
            client["account_key"], target["account_key"], client["token"], str(uuid4()), 2 ** 63
        )
    else:
        status, response = RequestGenerator.POST_account_withdraw(
            client["account_key"], client["token"], str(uuid4()), 2 ** 63
        )

    assert status == 400
    assert response["code"] == "QIT000001"
    assert ObjectGenerator.get_balance(client) == 1000
    assert ObjectGenerator.get_balance(target) == 0


def test_extract_supports_the_last_calendar_date():
    client = ObjectGenerator.create_active_client(balance=100)

    status, response = RequestGenerator.GET_account_extract(
        client["account_key"], client["token"], {"end_date": "9999-12-31"}
    )

    assert status == 200
    assert len(response["data"]) == 1
