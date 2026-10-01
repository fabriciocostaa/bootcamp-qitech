from controllers.base_controller import BaseController
from repositories.account_repository import AccountRepository
from errors import NotFoundAccount, InvalidAmount, AccountNotActive, InsufficientBalance, SameAccountTransfer, InvalidDate, AccountNotOwnedByClient
from models import AccountStatus, TransactionType, Account
from datetime import date
from dtos.account_dto import accountDTO
from sqlalchemy.exc import IntegrityError

class AccountController(BaseController):
    def __init__(self) ->None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context) #compartilham o mesmo contexto, e portanto a mesma sessão, e portanto a mesma transação

    def _check_account_ownership(self, account: Account) -> None:
        if account.client.client_key != self.context.authenticated_client_key:
            raise AccountNotOwnedByClient()
    
    def deposit(self, account_key: str, amount: float, idempotency_key: str = None):
        endpoint = "POST /account/deposit"
        request_hash = self._hash_request(account_key=account_key, amount=amount)

        cached_response = self._check_idempotency(idempotency_key, endpoint, request_hash)
        if cached_response is not None:
            return cached_response
        
        account = self.account_repository.get_by_key_for_update(account_key)

        if account is None:
            raise NotFoundAccount(account_key)
        
        if amount <= 0:
            raise InvalidAmount(amount)

        if not isinstance(amount, int):
            raise InvalidAmount(amount)

        if account.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_key)

        self.account_repository.register_transaction(account, TransactionType.DEPOSIT, amount)

        response = accountDTO.only_obj_key(account)

        if idempotency_key is not None:
            self.idempotency_repository.create(idempotency_key, endpoint, request_hash, response)

        try:
            self.session.commit()
        except IntegrityError:
            # Perdeu a corrida: outra requisição, com a MESMA chave, já
            # commitou primeiro. Desfaz o que essa tentou fazer e devolve
            # a resposta de quem chegou primeiro — não processa de novo.
            self.session.rollback()
            existing = self.idempotency_repository.get_by_key(idempotency_key, endpoint)
            return existing.response_body

        return response

    def withdraw(self, account_key: str, amount: float, idempotency_key: str=None):
        endpoint = "POST /account/withdraw"
        request_hash = self._hash_request(account_key=account_key, amount=amount)

        cached_response = self._check_idempotency(idempotency_key, endpoint, request_hash)
        if cached_response is not None:
            return cached_response
        
        account = self.account_repository.get_by_key_for_update(account_key)

        if account is None:
            raise NotFoundAccount(account_key)

        self._check_account_ownership(account)
        
        if amount <= 0:
            raise InvalidAmount(amount)

        if not isinstance(amount, int):
            raise InvalidAmount(amount)

        if account.balance < amount:
            raise InsufficientBalance(account_key, account.balance)

        if account.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_key)

        self.account_repository.register_transaction(account, TransactionType.WITHDRAW, amount)

        response = accountDTO.only_obj_key(account)

        if idempotency_key is not None:
            self.idempotency_repository.create(idempotency_key, endpoint, request_hash, response)

        try:
            self.session.commit()
        except IntegrityError:
            # Perdeu a corrida: outra requisição, com a MESMA chave, já
            # commitou primeiro. Desfaz o que essa tentou fazer e devolve
            # a resposta de quem chegou primeiro — não processa de novo.
            self.session.rollback()
            existing = self.idempotency_repository.get_by_key(idempotency_key, endpoint)
            return existing.response_body

        return response

    def transfer(self, account_from_key: str, account_to_key: str, amount: float, idempotency_key: str=None):
        endpoint = "POST /account/transfer"
        request_hash = self._hash_request(account_key=account_from_key, amount=amount)
        
        cached_response = self._check_idempotency(idempotency_key, endpoint, request_hash)
        if cached_response is not None:
            return cached_response
        
        if amount <= 0:
            raise InvalidAmount(amount)

        if not isinstance(amount, int):
            raise InvalidAmount(amount)

        if account_from_key == account_to_key:
            raise SameAccountTransfer(account_from_key)

        account_from, account_to = self.account_repository.get_two_by_key_for_update(account_from_key, account_to_key)

        if account_from is None:
            raise NotFoundAccount(account_from_key)

        self._check_account_ownership(account_from)

        if account_to is None:
            raise NotFoundAccount(account_to_key)

        if account_from.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_from_key)

        if account_to.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_to_key)

        tax = int(amount * 0.02)
        total_debited = amount + tax

        if account_from.balance < total_debited:
            raise InsufficientBalance(account_from_key, account_from.balance)

        self.account_repository.register_transfer(account_from, account_to, amount, tax)

        response = accountDTO.only_obj_key(account_from)

        if idempotency_key is not None:
            self.idempotency_repository.create(idempotency_key, endpoint, request_hash, response)

        try:
            self.session.commit()
        except IntegrityError:
            # Perdeu a corrida: outra requisição, com a MESMA chave, já
            # commitou primeiro. Desfaz o que essa tentou fazer e devolve
            # a resposta de quem chegou primeiro — não processa de novo.
            self.session.rollback()
            existing = self.idempotency_repository.get_by_key(idempotency_key, endpoint)
            return existing.response_body

        return response

    def extract(self, account_key: str, limit: int, offset: int, filters: dict)-> list:
        start_date = filters.get("start_date")
        end_date = filters.get("end_date")

        if start_date is not None:
            start_date = self._parse_date(start_date)
            filters["start_date"] = start_date

        if end_date is not None:
            end_date = self._parse_date(end_date)
            filters["end_date"] = end_date

        if start_date is not None and end_date is not None:
            if start_date > end_date:
                raise InvalidDate(start_date, end_date)
        
        account = self.account_repository.get_by_key(account_key)

        if account is None:
            raise NotFoundAccount(account_key)
        
        self._check_account_ownership(account)
        extract = self.account_repository.list_page(account, limit + 1, offset, filters)

        is_last_page = True
        if len(extract) > limit:
            is_last_page = False
            extract = extract[:-1]

        return {
            "account_extract": accountDTO.list_extract_to_list_dict(extract),
            "is_last_page": is_last_page,
        }

    def _parse_date(self, raw_date: str):
        """Converte a data, ou recusa com 422 em vez de 500."""
        try:
            return date.fromisoformat(raw_date)
        except ValueError:
            raise InvalidDate(f"Invalid date format: {raw_date}. Expected format: YYYY-MM-DD")