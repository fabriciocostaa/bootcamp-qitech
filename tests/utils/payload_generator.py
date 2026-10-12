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
        today = date.today()
        try:
            return date(today.year - 18, today.month, today.day).isoformat()
        except ValueError:
            return date(today.year - 18, 2, 28).isoformat()

    @staticmethod
    def birthdate_turning_18_tomorrow() -> str:
        tomorrow = date.today() + timedelta(days=1)
        try:
            return date(tomorrow.year - 18, tomorrow.month, tomorrow.day).isoformat()
        except ValueError:
            return date(tomorrow.year - 18, 3, 1).isoformat()

    @staticmethod
    def birthdate_in_the_future() -> str:
        return (date.today() + timedelta(days=365)).isoformat()
