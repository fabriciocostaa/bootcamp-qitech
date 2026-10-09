from datetime import date, timedelta
from uuid import uuid4

from tests.utils.random_generator import RandomGenerator


class PayloadGenerator:
    @staticmethod
    def create_client_payload(
        name: str = None,
        email: str = None,
        document_number: str = None,
        password: str = None,
        birthdate: str = None,
    ) -> dict:
        """Um cadastro valido, com qualquer campo trocado a pedido.

        Sem argumento nenhum o payload sai aleatorio no que precisa ser
        unico (e-mail e CPF), pra que dois cadastros seguidos nao batam
        na regra de duplicidade. Quem testa FILTRO precisa do contrario
        disso: um valor conhecido, pra poder procurar por ele depois.

        O CPF padrao nunca contem "99": o mock do KYC recusa esses CPFs, e
        um cadastro "valido" que nasce recusado deixaria o teste instavel.
        """
        if name is None:
            name = "Maria da Silva"

        if email is None:
            email = f"maria.silva.{uuid4()}@exemplo.com.br"

        if document_number is None:
            document_number = RandomGenerator.generate_cpf()

        if birthdate is None:
            birthdate = "1990-05-17"

        if password is None:
            password = "senhamaria123"

        return {
            "name": name,
            "email": email,
            "document_number": document_number,
            "password": password,
            "birthdate": birthdate,
        }

    @staticmethod
    def create_new_status_payload(new_status: str = None) -> dict:
        return {"status": new_status}

    @staticmethod
    def create_client_auth_payload(document_number: str, password: str) -> dict:
        return {"document_number": document_number, "password": password}

    @staticmethod
    def birthdate_turning_18_today() -> str:
        """Quem faz 18 anos HOJE: ja e maior de idade (limite inferior do aceito)."""
        today = date.today()
        try:
            return date(today.year - 18, today.month, today.day).isoformat()
        except ValueError:  # hoje e 29/02 e o ano-alvo nao e bissexto
            return date(today.year - 18, 2, 28).isoformat()

    @staticmethod
    def birthdate_turning_18_tomorrow() -> str:
        """Quem faz 18 anos AMANHA: ainda tem 17 (limite superior do recusado)."""
        tomorrow = date.today() + timedelta(days=1)
        try:
            return date(tomorrow.year - 18, tomorrow.month, tomorrow.day).isoformat()
        except ValueError:  # amanha e 29/02: o dia seguinte do ano-alvo ainda e menor de idade
            return date(tomorrow.year - 18, 3, 1).isoformat()

    @staticmethod
    def birthdate_in_the_future() -> str:
        return (date.today() + timedelta(days=365)).isoformat()
