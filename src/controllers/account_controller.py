from controllers.base_controller import BaseController
from repositories.account_repository import AccountRepository
from errors import NotFoundAccount, InvalidAmount, AccountNotActive, InsufficientBalance, SameAccountTransfer, InvalidDate
from models import AccountStatus, TransactionType
from datetime import date
from dtos.account_dto import accountDTO

class AccountController(BaseController):
    def __init__(self) ->None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context) #compartilham o mesmo contexto, e portanto a mesma sessão, e portanto a mesma transação

    def deposit(self, account_key: str, amount: float):
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

        self.session.commit()
        return accountDTO.only_obj_key(account)

    def withdraw(self, account_key: str, amount: float):
        account = self.account_repository.get_by_key_for_update(account_key)

        if account is None:
            raise NotFoundAccount(account_key)
        
        if amount <= 0:
            raise InvalidAmount(amount)

        if not isinstance(amount, int):
            raise InvalidAmount(amount)

        if account.balance < amount:
            raise InsufficientBalance(account_key, account.balance)

        if account.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_key)

        self.account_repository.register_transaction(account, TransactionType.WITHDRAW, amount)

        self.session.commit()
        return accountDTO.only_obj_key(account)

    def transfer(self, account_from_key: str, account_to_key: str, amount: float):
        if amount <= 0:
            raise InvalidAmount(amount)

        if not isinstance(amount, int):
            raise InvalidAmount(amount)

        if account_from_key == account_to_key:
            raise SameAccountTransfer(account_from_key)

        account_from, account_to = self.account_repository.get_two_by_key_for_update(account_from_key, account_to_key)

        if account_from is None:
            raise NotFoundAccount(account_from_key)

        if account_to is None:
            raise NotFoundAccount(account_to_key)

        if account_from.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_from_key)

        if account_to.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_to_key)

        if account_from.balance < amount:
                raise InsufficientBalance(account_from_key, account_from.balance)

        self.account_repository.register_transfer(account_from, account_to, amount)
        self.session.commit()
        return accountDTO.only_obj_key(account_from)

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