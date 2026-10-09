from uuid import uuid4

from tests.utils import ObjectGenerator, RandomGenerator, RequestGenerator
from tests.utils.markers import known_bug
from tests.utils.random_generator import RISK_LOW_SCORE_FRAGMENT, RISK_UNAVAILABLE_FRAGMENT


def active_client_with_document(fragment: str) -> dict:
    """Cliente aprovado cujo CPF faz o mock do bureau de risco reagir (88 = score baixo, 77 = fora do ar)."""
    client = ObjectGenerator.create_client(document_number=RandomGenerator.generate_cpf_containing(fragment))
    client["token"] = ObjectGenerator.create_client_auth(client["document_number"], client["password"])["token"]
    return client


class TestCreditRequest:
    """POST /client/{key}/credit — pede uma linha de credito (depende do bureau de risco)."""

    def test_approved_credit_line(self):
        client = ObjectGenerator.create_active_client()

        status, response = RequestGenerator.POST_credit(client["client_key"], client["token"])

        assert status == 201
        assert response["status"] == "APPROVED"
        assert response["limit_cents"] > 0
        assert response["credit_line_key"]

    def test_low_score_is_rejected_with_a_reason_not_an_error(self):
        """Score baixo nao e falha do sistema: e um desfecho de negocio (422 + REJECTED)."""
        client = active_client_with_document(RISK_LOW_SCORE_FRAGMENT)

        status, response = RequestGenerator.POST_credit(client["client_key"], client["token"])

        assert status == 422
        assert response["status"] == "REJECTED"
        assert response["reason"]

    def test_rejected_request_does_not_leave_a_usable_credit_line(self):
        client = active_client_with_document(RISK_LOW_SCORE_FRAGMENT)
        RequestGenerator.POST_credit(client["client_key"], client["token"])

        status, response = RequestGenerator.POST_credit_withdraw(client["client_key"], client["token"], str(uuid4()), 1000)

        assert status == 422
        assert response["status"] == "REJECTED"

    def test_risk_service_down_is_a_controlled_error_not_a_500(self):
        client = active_client_with_document(RISK_UNAVAILABLE_FRAGMENT)

        status, response = RequestGenerator.POST_credit(client["client_key"], client["token"])

        assert status == 422
        assert response["status"] == "ERROR"
        assert response["reason"]

    def test_unknown_client(self):
        client = ObjectGenerator.create_active_client()

        status, response = RequestGenerator.POST_credit(str(uuid4()), client["token"])

        assert status == 404
        assert response["code"] == "QIT001001"

    def test_requires_authentication(self):
        client = ObjectGenerator.create_active_client()

        status, response = RequestGenerator.POST_credit(client["client_key"], None)

        assert status == 401
        assert response["code"] == "QIT003002"

    @known_bug("BUG-CREDIT-OWNERSHIP", "as rotas de credito nao checam o dono: qualquer cliente logado abre credito no nome de outro")
    def test_cannot_open_credit_for_another_client(self):
        victim = ObjectGenerator.create_active_client()
        intruder = ObjectGenerator.create_active_client()

        status, response = RequestGenerator.POST_credit(victim["client_key"], intruder["token"])

        assert status == 401
        assert response["code"] == "QIT003005"
