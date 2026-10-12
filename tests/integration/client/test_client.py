from uuid import uuid4

import pytest

from tests.utils import DbUtils, ObjectGenerator, PayloadGenerator, RequestGenerator


def extract_keys(response: dict) -> list:
    return [client["client_key"] for client in response["data"]]


class TestClientsAccess:
    def test_client_cannot_list_clients(self):
        _client, token = ObjectGenerator.create_authenticated_client()

        status, response = RequestGenerator.GET_clients(token)

        assert status == 403
        assert response["code"] == "QIT003006"

    def test_requires_authentication(self):
        status, response = RequestGenerator.GET_clients(None)

        assert status == 401
        assert response["code"] == "QIT003001"


class TestClients:
    def test_get_pages(self, operator_token):
        DbUtils.rollback()

        status, response = RequestGenerator.GET_clients(operator_token)
        assert status == 200
        baseline = len(response["data"])

        for _entidade in range(3):
            status, _response = RequestGenerator.POST_client(PayloadGenerator.create_client_payload())
            assert status == 201
        total = baseline + 3

        status, response = RequestGenerator.GET_clients(operator_token, {"limit": 100})
        assert status == 200
        assert len(response["data"]) == total
        assert response["is_last_page"] is True
        assert response["limit"] == 100
        assert response["page"] == 0

        status, response = RequestGenerator.GET_clients(operator_token, {"limit": 2})
        assert status == 200
        assert len(response["data"]) == 2
        assert response["is_last_page"] is False

        last_page = (total - 1) // 2
        status, response = RequestGenerator.GET_clients(operator_token, {"limit": 2, "page": last_page})
        assert status == 200
        assert len(response["data"]) == total - 2 * last_page
        assert response["is_last_page"] is True

    def test_empty_database_gives_an_empty_last_page(self, operator_token):
        DbUtils.rollback()

        status, response = RequestGenerator.GET_clients(operator_token)

        assert status == 200
        assert isinstance(response["data"], list)
        assert response["is_last_page"] is True

    def test_page_exactly_full_is_the_last_page(self, operator_token):
        batch = f"Limite{uuid4().hex[:8]}"
        for _ in range(3):
            ObjectGenerator.create_client(name=batch)

        status, response = RequestGenerator.GET_clients(operator_token, {"name": batch, "limit": 3})

        assert status == 200
        assert len(response["data"]) == 3
        assert response["is_last_page"] is True

    def test_page_beyond_the_end_is_empty(self, operator_token):
        batch = f"Alem{uuid4().hex[:8]}"
        ObjectGenerator.create_client(name=batch)

        status, response = RequestGenerator.GET_clients(operator_token, {"name": batch, "page": 5})

        assert status == 200
        assert response["data"] == []
        assert response["is_last_page"] is True

    def test_get_filtered(self, operator_token):
        DbUtils.rollback()

        approved = ObjectGenerator.create_client()
        rejected_a = ObjectGenerator.create_rejected_client()
        rejected_b = ObjectGenerator.create_rejected_client()

        status, response = RequestGenerator.GET_clients(operator_token, {"status": "approved"})
        assert status == 200
        assert approved["client_key"] in extract_keys(response)
        assert rejected_a["client_key"] not in extract_keys(response)

        status, response = RequestGenerator.GET_clients(operator_token, {"status": "rejected"})
        assert status == 200
        assert sorted(extract_keys(response)) == sorted([rejected_a["client_key"], rejected_b["client_key"]])
        assert response["is_last_page"] is True

    def test_wrong_params(self, operator_token):
        for params in [{"page": -3}, {"limit": 500}, {"limit": 101}, {"limit": -1}, {"limit": "abc"}, {"page": "abc"}, {"page": 1.5}]:
            status, response = RequestGenerator.GET_clients(operator_token, params)
            assert status == 400, params
            assert response["code"] == "QIT000001"

    def test_limit_boundaries_are_accepted(self, operator_token):
        for limit in [1, 100]:
            status, response = RequestGenerator.GET_clients(operator_token, {"limit": limit})
            assert status == 200, f"limit={limit} foi recusado"
            assert response["limit"] == limit

    def test_refuses_limit_zero(self, operator_token):
        status, response = RequestGenerator.GET_clients(operator_token, {"limit": 0})

        assert status == 400
        assert response["code"] == "QIT000001"

    def test_list_does_not_carry_the_status_trail(self, operator_token):
        payload = PayloadGenerator.create_client_payload()
        status, response = RequestGenerator.POST_client(payload)
        assert status == 201
        created_key = response["client_key"]

        status, response = RequestGenerator.GET_clients(operator_token, {"document_number": payload["document_number"]})
        assert status == 200
        assert extract_keys(response) == [created_key]
        item = response["data"][0]
        assert "status_events" not in item
        assert "accounts" not in item
        assert item["status"] == "approved"
        assert "password" not in item and "password_hash" not in item

    def test_refuses_unknown_query_param(self, operator_token):
        status, response = RequestGenerator.GET_clients(operator_token, {"stauts": "pending"})
        assert status == 400
        assert response["code"] == "QIT000001"

    def test_filters_by_partial_name_ignoring_case(self, operator_token):
        unique_surname = f"Zimmerman{uuid4().hex[:8]}"

        matching = ObjectGenerator.create_client(name=f"Ana {unique_surname}")
        ObjectGenerator.create_client(name="Bruno Carvalho")

        for term in [unique_surname.upper(), unique_surname.lower(), unique_surname[:6].upper()]:
            status, response = RequestGenerator.GET_clients(operator_token, {"name": term})
            assert status == 200
            assert matching["client_key"] in extract_keys(response), f"o termo {term!r} nao achou o cliente"

        status, response = RequestGenerator.GET_clients(operator_token, {"name": unique_surname.upper()})
        assert extract_keys(response) == [matching["client_key"]]

    def test_name_filter_treats_wildcards_literally(self, operator_token):
        batch = f"Coringa{uuid4().hex[:8]}"
        ObjectGenerator.create_client(name=f"{batch} Silva")

        status, response = RequestGenerator.GET_clients(operator_token, {"name": f"{batch}%Silva"})

        assert status == 200
        assert response["data"] == []

    def test_filters_by_exact_email_and_document_number(self, operator_token):
        client = ObjectGenerator.create_client()

        status, response = RequestGenerator.GET_clients(operator_token, {"email": client["email"]})
        assert status == 200
        assert extract_keys(response) == [client["client_key"]]

        status, response = RequestGenerator.GET_clients(operator_token, {"document_number": client["document_number"]})
        assert status == 200
        assert extract_keys(response) == [client["client_key"]]

        status, response = RequestGenerator.GET_clients(operator_token, {"email": client["email"][:10]})
        assert status == 200
        assert client["client_key"] not in extract_keys(response)

    def test_filter_by_unknown_document_number_is_empty(self, operator_token):
        status, response = RequestGenerator.GET_clients(operator_token, {"document_number": "000.000.000-00"})

        assert status == 200
        assert response["data"] == []
        assert response["is_last_page"] is True

    def test_refuses_malformed_document_number_filter(self, operator_token):
        status, response = RequestGenerator.GET_clients(operator_token, {"document_number": "12345"})

        assert status == 400
        assert response["code"] == "QIT000001"

    def test_filters_by_inclusive_birthdate_range(self, operator_token):
        family_name = f"Bernoulli{uuid4().hex[:8]}"
        birthdates = ["1931-01-01", "1931-01-02", "1931-01-03", "1931-01-04"]

        created_keys = []
        for birthdate in birthdates:
            created_keys.append(ObjectGenerator.create_client(name=family_name, birthdate=birthdate)["client_key"])

        status, response = RequestGenerator.GET_clients(
            operator_token, {"name": family_name, "birthdate_from": "1931-01-02", "birthdate_to": "1931-01-03"}
        )
        assert status == 200
        assert sorted(extract_keys(response)) == sorted([created_keys[1], created_keys[2]])

    def test_birthdate_range_with_only_one_end(self, operator_token):
        family_name = f"Euler{uuid4().hex[:8]}"
        old = ObjectGenerator.create_client(name=family_name, birthdate="1940-06-01")["client_key"]
        young = ObjectGenerator.create_client(name=family_name, birthdate="1980-06-01")["client_key"]

        _status, only_from = RequestGenerator.GET_clients(operator_token, {"name": family_name, "birthdate_from": "1960-01-01"})
        _status, only_to = RequestGenerator.GET_clients(operator_token, {"name": family_name, "birthdate_to": "1960-01-01"})

        assert extract_keys(only_from) == [young]
        assert extract_keys(only_to) == [old]

    def test_combines_filters_with_and(self, operator_token):
        team_name = f"Curie{uuid4().hex[:8]}"

        ObjectGenerator.create_client(name=team_name, birthdate="1940-03-01")
        younger = ObjectGenerator.create_client(name=team_name, birthdate="1960-03-01")

        status, response = RequestGenerator.GET_clients(operator_token, {"name": team_name, "birthdate_from": "1950-01-01"})
        assert status == 200
        assert extract_keys(response) == [younger["client_key"]]

    def test_lists_newest_first_and_pages_do_not_overlap(self, operator_token):
        batch_name = f"Noether{uuid4().hex[:8]}"

        created_keys = [ObjectGenerator.create_client(name=batch_name)["client_key"] for _ in range(3)]
        created_keys.reverse()

        status, response = RequestGenerator.GET_clients(operator_token, {"name": batch_name, "limit": 2})
        assert status == 200
        assert extract_keys(response) == created_keys[:2]
        assert response["is_last_page"] is False

        status, response = RequestGenerator.GET_clients(operator_token, {"name": batch_name, "limit": 2, "page": 1})
        assert status == 200
        assert extract_keys(response) == created_keys[2:]
        assert response["is_last_page"] is True

    def test_refuses_inverted_birthdate_range(self, operator_token):
        status, response = RequestGenerator.GET_clients(
            operator_token, {"birthdate_from": "2000-01-01", "birthdate_to": "1990-01-01"}
        )
        assert status == 400
        assert response["code"] == "QIT000010"

    def test_refuses_impossible_birthdate_filter(self, operator_token):
        status, response = RequestGenerator.GET_clients(operator_token, {"birthdate_from": "2025-02-30"})

        assert status == 422
        assert response["code"] == "QIT001007"

    def test_filters_by_more_than_one_status(self, operator_token):
        batch_name = f"Kovalevskaya{uuid4().hex[:8]}"
        approved = ObjectGenerator.create_client(name=batch_name)
        rejected = ObjectGenerator.create_rejected_client()

        status, response = RequestGenerator.GET_clients(operator_token, {"status": ["approved", "rejected"], "limit": 100})
        assert status == 200
        keys = extract_keys(response)
        assert approved["client_key"] in keys
        assert rejected["client_key"] in keys

        status, response = RequestGenerator.GET_clients(operator_token, {"name": batch_name, "status": ["rejected"]})
        assert status == 200
        assert response["data"] == []

        status, response = RequestGenerator.GET_clients(operator_token, {"name": batch_name, "status": ["approved"]})
        assert extract_keys(response) == [approved["client_key"]]

    def test_pending_filter_finds_nobody_after_signup(self, operator_token):
        batch_name = f"Pendente{uuid4().hex[:8]}"
        ObjectGenerator.create_client(name=batch_name)

        status, response = RequestGenerator.GET_clients(operator_token, {"name": batch_name, "status": "pending"})

        assert status == 200
        assert response["data"] == []

    def test_refuses_unknown_status_filter(self, operator_token):
        for statuses in [["status_que_nao_existe"], ["pending", "status_que_nao_existe"], ["failed"], ["APPROVED"]]:
            status, response = RequestGenerator.GET_clients(operator_token, {"status": statuses})
            assert status == 400, statuses
            assert response["code"] == "QIT000001"
