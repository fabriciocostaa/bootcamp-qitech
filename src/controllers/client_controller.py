from datetime import date
from sqlalchemy.exc import IntegrityError

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
    NotFoundClient,
    ClientFinalStatus,
    UnderageClient,
    AccountNotOwnedByClient
)
from models import Client, ClientStatus
from repositories import ClientRepository, AccountRepository, OperatorRepository
from utils.document_number import is_valid_cpf

MINIMUM_AGE = 18


class ClientController(BaseController):

    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context) 
        self.account_repository = AccountRepository(self.context)
        self.operator_repository = OperatorRepository(self.context)

    def get_status_history(self, client_key: str) -> dict:
        self.logger.debug(f"Buscando histórico do cliente {client_key}")

        client = self.client_repository.get_by_key(client_key)
        if client is None:
            raise NotFoundClient(client_key)

        self.require_operator()

        response = clientDTO.status_history_to_list(client.status_events)
        return response

    def create(self, client_data: dict, client_ip: str = "101.0.0.1") -> dict:
        self.logger.debug("Criando uma nova Client")

        document_number = client_data["document_number"]
        email = client_data["email"].lower()
        client_data["email"] = email
        birthdate = self._parse_birthdate(client_data["birthdate"])

        if not is_valid_cpf(document_number):
            raise InvalidDocumentNumber(document_number)

        if self.client_repository.get_by_document_number(document_number) is not None:
            raise DuplicatedDocumentNumber(document_number)

        if self.client_repository.get_by_email(email) is not None:
            raise DuplicatedEmail(email)

        age = self._age_in_years(birthdate)

        if age < MINIMUM_AGE:
            raise UnderageClient(age, MINIMUM_AGE)

        client = self.client_repository.create(client_data=client_data)
        try:
            self.session.flush()
        except IntegrityError:
            self.session.rollback()
            if self.client_repository.get_by_document_number(document_number) is not None:
                raise DuplicatedDocumentNumber(document_number)
            if self.client_repository.get_by_email(email) is not None:
                raise DuplicatedEmail(email)
            raise

        kyc_connector = KYCConnector()
        antifraud_connector = AntifraudConnector()

        kyc_response = kyc_connector.verify_identity(document_number, client_data["name"])

        if kyc_response.json.get("status") == "approved":
            
            fraud_response = antifraud_connector.analyze_risk(document_number, email, client_ip)
            
            if fraud_response.json.get("recommendation") == "allow":
        
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
        self.logger.debug(f"Buscando o cliente de chave {client_key}")

        client = self.client_repository.get_by_key(client_key)

        if client is None:
            raise NotFoundClient(client_key)

        is_owner = client.client_key == self.context.authenticated_client_key
        is_operator = self.context.authenticated_operator_key is not None

        if not is_owner and not is_operator:
            raise AccountNotOwnedByClient()

        return clientDTO.obj_to_dict(client)

    def get_list(self, limit: int, offset: int, filters: dict) -> dict:
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

        is_last_page = True
        if len(client_list) > limit:
            is_last_page = False
            client_list = client_list[:-1]

        return {
            "client_list_dto": clientDTO.list_obj_to_list_dict(client_list),
            "is_last_page": is_last_page,
        }

    def update_status(self, client_key: str, new_status: str) -> dict:
        self.require_operator() 
        client = self.client_repository.get_by_key(client_key)

        operator_key = self.operator_key()
        operator = self.operator_repository.get_by_key(operator_key) 
        
        if client is None:
            raise NotFoundClient(client_key)

        self._check_status_can_change(client, new_status)

        self.client_repository.update_status(client, new_status, operator)

        if new_status == ClientStatus.APPROVED:
            self.account_repository.create(client)

        client_dto = clientDTO.only_obj_key(client)
        self.session.commit()

        return client_dto


    def _check_status_can_change(self, client: Client, new_status: str) -> None:
        old_status = client.status.enumerator

        if old_status != ClientStatus.REJECTED:
            raise ClientFinalStatus(old_status, new_status)

    def _parse_birthdate(self, raw_birthdate: str) -> date:
        try:
            return date.fromisoformat(raw_birthdate)
        except ValueError:
            raise InvalidBirthdate(raw_birthdate)

    def _age_in_years(self, birthdate: date) -> int:
        today = date.today()
        age = today.year - birthdate.year

        if (today.month, today.day) < (birthdate.month, birthdate.day):
            age = age - 1

        return age
