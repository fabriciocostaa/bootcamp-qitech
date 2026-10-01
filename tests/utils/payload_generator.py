from uuid import uuid4

from tests.utils.random_generator import RandomGenerator


class PayloadGenerator:
    @staticmethod
    def create_client_payload(
        name: str = None,
        email: str = None,
        document_number: str = None,
        password: str= None,    #acrescentei senha aos clientes
        birthdate: str = None,
    ) -> dict:
        """Um cadastro valido, com qualquer campo trocado a pedido.

        Sem argumento nenhum o payload sai aleatorio no que precisa ser
        unico (e-mail e CPF), pra que dois cadastros seguidos nao batam
        na regra de duplicidade. Quem testa FILTRO precisa do contrario
        disso: um valor conhecido, pra poder procurar por ele depois.
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

        payload = {
            "name": name,
            "email": email,
            "document_number": document_number,
            "password": password,
            "birthdate": birthdate,
        }
        return payload

    @staticmethod
    def create_new_status_payload(new_status: str = None) -> dict:
        payload = {"status": new_status}
        return payload

    @staticmethod
    def create_client_auth_payload(document_number: str, password: str) -> dict:

        payload = {
            "document_number": document_number,
            "password": password
        }
        return payload
