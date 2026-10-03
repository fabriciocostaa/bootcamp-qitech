from datetime import date

from connectors.kyc_connector import KYCConnector
from connectors.antifraud_connector import AntifraudConnector

from controllers.base_controller import BaseController
from dtos import clientDTO
from errors import (
    DuplicatedDocumentNumber,
    DuplicatedEmail,
    InvalidBirthdate,
    InvalidDocumentNumber,
    InvalidParameter,
    NotFoundSampleEntity,
    SampleEntityFinalStatus,
    UnderageSampleEntity,
    OperatorRequired,
    AccountNotOwnedByClient
)
from models import Client, ClientStatus
from repositories import ClientRepository, AccountRepository
from utils.document_number import is_valid_cpf

# A faixa de idade aceita. Abaixo do mínimo o cadastro é RECUSADO; acima
# do máximo ele é CRIADO, mas já em "failed" — são desfechos diferentes,
# e o create lá embaixo mostra a diferença em duas linhas.
MINIMUM_AGE = 18
MAXIMUM_AGE = 80


class ClientController(BaseController):
    """As regras de negócio. Aqui mora o "pode" e o "não pode"."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context) 
        self.account_repository = AccountRepository(self.context)

    def create(self, client_data: dict, client_ip: str = "101.0.0.1") -> dict:
        """Confere quem está entrando, e só então cria.

        As quatro perguntas abaixo acontecem ANTES de qualquer escrita, e
        essa ordem é a regra: uma recusa não pode deixar meia entidade no
        banco. Repare que nenhuma delas é sobre FORMATO — isso o schema
        já cobrou lá na porta. Aqui é sobre o que só se sabe olhando o
        mundo: se o número existe, se alguém já usou, que idade a pessoa
        tem hoje.
        """
        self.logger.debug("Criando uma nova Client")

        document_number = client_data["document_number"]
        email = client_data["email"]
        birthdate = self._parse_birthdate(client_data["birthdate"])

        if not is_valid_cpf(document_number):
            raise InvalidDocumentNumber(document_number)

        if self.client_repository.get_by_document_number(document_number) is not None:
            raise DuplicatedDocumentNumber(document_number)

        if self.client_repository.get_by_email(email) is not None:
            raise DuplicatedEmail(email)

        age = self._age_in_years(birthdate)

        if age < MINIMUM_AGE:
            raise UnderageSampleEntity(age, MINIMUM_AGE)

        client = self.client_repository.create(client_data=client_data)

        # Passar da idade máxima não impede o cadastro: ele nasce em
        # "failed". É a diferença entre recusar o pedido e aceitá-lo com
        # outro desfecho — e as duas regras moram lado a lado de
        # propósito, pra que a diferença fique à vista.
        if age > MAXIMUM_AGE:
            self.client_repository.update_status(client, ClientStatus.REJECTED)
        else:
            self.client_repository.update_status(client, ClientStatus.PENDING)
            self.session.flush()

            kyc_connector = KYCConnector()
            antifraud_connector = AntifraudConnector()

            kyc_response = kyc_connector.verify_identity(document_number, client_data["name"])

            if kyc_response.status == 200:
                
                fraud_response = antifraud_connector.analyze_risk(document_number, email, client_ip)
                
                if fraud_response.status == 200:
            
                    self.client_repository.update_status(client, ClientStatus.APPROVED)
                    self.account_repository.create(client)

                else:
                    self.client_repository.update_status(client, ClientStatus.REJECTED)
            else:
                
                self.client_repository.update_status(client, ClientStatus.REJECTED)

        client_dto = clientDTO.only_obj_key(client)
        self.session.commit()

        return client_dto

        

    def get_by_key(self, client_key: str) -> dict:
        self.logger.debug(f"Buscando a entidade de chave {client_key}")

        client = self.client_repository.get_by_key(client_key)

        if client is None:
            raise NotFoundSampleEntity(client_key)

        is_owner = client.client_key == self.context.authenticated_client_key
        is_operator = self.context.authenticated_operator_key is not None

        if not is_owner and not is_operator:
            raise AccountNotOwnedByClient(client_key)

        return clientDTO.obj_to_dict(client)

    def get_list(self, limit: int, offset: int, filters: dict) -> dict:
        """A pagina pedida, depois de conferir se o pedido faz sentido.

        Um intervalo de nascimento de cabeca pra baixo — comeco depois
        do fim — nunca pode achar ninguem. Devolver zero linhas nesse
        caso mente por omissao: parece que a busca rodou e nao
        encontrou, quando na verdade a pergunta e que nao tinha
        resposta possivel.

        Quem decide que um pedido nao pode ser respondido e este
        controller. O resource fala HTTP, nao julga pedido.

        Repare no que NAO esta mais aqui: a lista de status validos.
        Aquilo era conferir se um valor pertence a um conjunto fixo —
        exatamente o que um `enum` de JSON Schema faz, e agora faz, no
        src/schemas/get_sample_entities.json. O que sobrou e o que
        nenhum schema sabe fazer: comparar dois campos ENTRE SI.
        """
        self.require_operator()        
        birthdate_from = filters.get("birthdate_from")
        birthdate_to = filters.get("birthdate_to")

        if birthdate_from is not None:
            birthdate_from = self._parse_birthdate(birthdate_from)
            filters["birthdate_from"] = birthdate_from

        if birthdate_to is not None:
            birthdate_to = self._parse_birthdate(birthdate_to)
            filters["birthdate_to"] = birthdate_to

        if birthdate_from is not None and birthdate_to is not None:
            if birthdate_from > birthdate_to:
                raise InvalidParameter(
                    f"birthdate_from ({birthdate_from}) is after birthdate_to ({birthdate_to})"
                )

        client_list = self.client_repository.list_page(limit, offset, filters)

        # Pedimos um a mais que o limite só pra saber se existe próxima
        # página. Se veio o extra, ele não entra na resposta.
        is_last_page = True
        if len(client_list) > limit:
            is_last_page = False
            client_list = client_list[:-1]

        return {
            "client_list_dto": clientDTO.list_obj_to_list_dict(client_list),
            "is_last_page": is_last_page,
        }

    def update_status(self, client_key: str, new_status: str) -> dict:
        client = self.client_repository.get_by_key(client_key)

        if client is None:
            raise NotFoundSampleEntity(client_key)

        self._check_status_can_change(client, new_status)

        self.client_repository.update_status(client, new_status)

        #Aprovação de cadastro de cliente, cria conta com saldo 0
        if new_status == ClientStatus.APPROVED:
            self.account_repository.create(client)

        client_dto = clientDTO.only_obj_key(client)
        self.session.commit()

        return client_dto


    def _check_status_can_change(self, client: Client, new_status: str) -> None:
        old_status = client.status.enumerator

        if old_status != ClientStatus.PENDING:
            raise SampleEntityFinalStatus(old_status, new_status)

    def _parse_birthdate(self, raw_birthdate: str) -> date:
        """Converte a data, ou recusa com 422 em vez de 500.

        O schema já garantiu o FORMATO (quatro dígitos, traço, dois,
        traço, dois). O que ele não sabe é quantos dias fevereiro tem —
        um `pattern` conta caracteres, não consulta calendário. Por isso
        "2025-02-30" chega aqui intacto, e é aqui que ele para.
        """
        try:
            return date.fromisoformat(raw_birthdate)
        except ValueError:
            raise InvalidBirthdate(raw_birthdate)

    def _age_in_years(self, birthdate: date) -> int:
        today = date.today()
        age = today.year - birthdate.year

        # Quem ainda não fez aniversário este ano tem um ano a menos do
        # que a subtração acima diz.
        if (today.month, today.day) < (birthdate.month, birthdate.day):
            age = age - 1

        return age
