from os import environ
from uuid import uuid4

import pytest

from tests.utils import ObjectGenerator, RequestGenerator
from tests.utils.money import expected_transfer_fee, to_cents


def transfer(origin, destination_account_key, amount, key=None, account_key=None, token=None):
    return RequestGenerator.POST_account_transfer(
        account_key or origin["account_key"], destination_account_key, token or origin["token"], key or str(uuid4()), amount
    )


class TestTransfer:
    def test_transfer_moves_money_and_charges_the_fee(self):
        origin = ObjectGenerator.create_active_client(balance=10000)
        destination = ObjectGenerator.create_active_client()
        fee = expected_transfer_fee(1000)

        status, response = transfer(origin, destination["account_key"], 1000)

        assert status == 200
        assert response["kind"] == "transfer"
        assert response["amount"] == "10.00"
        assert to_cents(response["fee"]) == fee
        assert ObjectGenerator.get_balance(origin) == 10000 - 1000 - fee
        assert ObjectGenerator.get_balance(destination) == 1000

    def test_fee_goes_to_the_banks_revenue_account(self, operator_token):
        document = environ["ACCOUNT_DOCUMENT_NUMBER"]
        origin = ObjectGenerator.create_active_client(balance=50000)
        destination = ObjectGenerator.create_active_client()
        before = ObjectGenerator.get_balance_by_document(document, operator_token)

        status, _response = transfer(origin, destination["account_key"], 10000)
        assert status == 200

        after = ObjectGenerator.get_balance_by_document(document, operator_token)
        assert after - before == expected_transfer_fee(10000)

    def test_money_is_conserved_across_origin_destination_and_revenue(self, operator_token):
        document = environ["ACCOUNT_DOCUMENT_NUMBER"]
        origin = ObjectGenerator.create_active_client(balance=30000)
        destination = ObjectGenerator.create_active_client(balance=700)
        total_before = (
            ObjectGenerator.get_balance(origin)
            + ObjectGenerator.get_balance(destination)
            + ObjectGenerator.get_balance_by_document(document, operator_token)
        )

        status, _response = transfer(origin, destination["account_key"], 12345)
        assert status == 200

        total_after = (
            ObjectGenerator.get_balance(origin)
            + ObjectGenerator.get_balance(destination)
            + ObjectGenerator.get_balance_by_document(document, operator_token)
        )
        assert total_after == total_before

    @pytest.mark.parametrize("amount", [1, 49, 50, 51, 99, 100, 101, 12345])
    def test_fee_is_always_rounded_up(self, amount):
        fee = expected_transfer_fee(amount)
        origin = ObjectGenerator.create_active_client(balance=amount + fee)
        destination = ObjectGenerator.create_active_client()

        status, response = transfer(origin, destination["account_key"], amount)

        assert status == 200
        assert to_cents(response["fee"]) == fee
        assert fee >= 1, "a taxa nunca e zero (arredonda pra cima)"
        assert ObjectGenerator.get_balance(origin) == 0
        assert ObjectGenerator.get_balance(destination) == amount

    def test_balance_covering_exactly_amount_plus_fee_is_enough(self):
        amount = 1000
        origin = ObjectGenerator.create_active_client(balance=amount + expected_transfer_fee(amount))
        destination = ObjectGenerator.create_active_client()

        status, _response = transfer(origin, destination["account_key"], amount)

        assert status == 200
        assert ObjectGenerator.get_balance(origin) == 0

    def test_one_cent_short_of_amount_plus_fee_is_refused_and_nothing_moves(self, operator_token):
        document = environ["ACCOUNT_DOCUMENT_NUMBER"]
        amount = 1000
        origin = ObjectGenerator.create_active_client(balance=amount + expected_transfer_fee(amount) - 1)
        destination = ObjectGenerator.create_active_client()
        revenue_before = ObjectGenerator.get_balance_by_document(document, operator_token)

        status, response = transfer(origin, destination["account_key"], amount)

        assert status == 422
        assert response["code"] == "QIT002003"
        assert ObjectGenerator.get_balance(origin) == amount + expected_transfer_fee(amount) - 1
        assert ObjectGenerator.get_balance(destination) == 0
        assert ObjectGenerator.get_balance_by_document(document, operator_token) == revenue_before

    def test_transferring_the_whole_balance_is_refused_because_of_the_fee(self):
        origin = ObjectGenerator.create_active_client(balance=1000)
        destination = ObjectGenerator.create_active_client()

        status, response = transfer(origin, destination["account_key"], 1000)

        assert status == 422
        assert response["code"] == "QIT002003"
        assert ObjectGenerator.get_balance(origin) == 1000

    def test_cannot_transfer_to_the_same_account(self):
        origin = ObjectGenerator.create_active_client(balance=5000)

        status, response = transfer(origin, origin["account_key"], 100)

        assert status == 422
        assert response["code"] == "QIT002005"
        assert ObjectGenerator.get_balance(origin) == 5000

    def test_unknown_destination_account(self):
        origin = ObjectGenerator.create_active_client(balance=5000)

        status, response = transfer(origin, str(uuid4()), 100)

        assert status == 404
        assert response["code"] == "QIT002001"
        assert ObjectGenerator.get_balance(origin) == 5000

    def test_unknown_origin_account(self):
        origin = ObjectGenerator.create_active_client(balance=5000)
        destination = ObjectGenerator.create_active_client()

        status, response = transfer(origin, destination["account_key"], 100, account_key=str(uuid4()))

        assert status == 404
        assert response["code"] == "QIT002001"

    def test_cannot_transfer_out_of_another_clients_account(self):
        owner = ObjectGenerator.create_active_client(balance=5000)
        intruder = ObjectGenerator.create_active_client()

        status, response = transfer(intruder, intruder["account_key"], 100, account_key=owner["account_key"])
        assert status == 401
        assert response["code"] == "QIT003005"

        assert ObjectGenerator.get_balance(owner) == 5000

    def test_float_amount_is_refused_by_the_business_rule(self):
        origin = ObjectGenerator.create_active_client(balance=5000)
        destination = ObjectGenerator.create_active_client()

        status, response = transfer(origin, destination["account_key"], 10.5)

        assert status == 422
        assert response["code"] == "QIT002004"
        assert ObjectGenerator.get_balance(origin) == 5000

    def test_missing_destination_and_extra_fields(self):
        origin = ObjectGenerator.create_active_client(balance=5000)
        headers = RequestGenerator.build_headers(origin["token"], str(uuid4()))
        path = f"/account/{origin['account_key']}/transfer"

        for body in [{"amount": 100}, {"account_to_key": str(uuid4())}, {"account_to_key": str(uuid4()), "amount": 100, "x": 1}]:
            response = RequestGenerator.send_raw("POST", path, headers=headers, payload=body)
            assert response.response_status == 400, body
            assert response.response_json["code"] == "QIT000001"

    def test_missing_idempotency_key(self):
        origin = ObjectGenerator.create_active_client(balance=5000)
        destination = ObjectGenerator.create_active_client()

        status, response = RequestGenerator.POST_account_transfer(
            origin["account_key"], destination["account_key"], origin["token"], None, 100
        )

        assert status == 400
        assert response["code"] == "QIT003008"

    def test_requires_authentication(self):
        origin = ObjectGenerator.create_active_client(balance=5000)
        destination = ObjectGenerator.create_active_client()

        status, response = RequestGenerator.POST_account_transfer(
            origin["account_key"], destination["account_key"], None, str(uuid4()), 100
        )

        assert status == 401
        assert response["code"] == "QIT003001"

    def test_recipient_can_spend_what_it_received(self):
        origin = ObjectGenerator.create_active_client(balance=10000)
        destination = ObjectGenerator.create_active_client()
        transfer(origin, destination["account_key"], 3000)

        status, _response = RequestGenerator.POST_account_withdraw(
            destination["account_key"], destination["token"], str(uuid4()), 3000
        )

        assert status == 200
        assert ObjectGenerator.get_balance(destination) == 0
