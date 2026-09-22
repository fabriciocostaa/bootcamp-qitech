from controllers.base_controller import BaseController
from repositories.account_repository import AccountRepository
from errors import NotFoundAccount, InvalidAmount, AccountNotActive, InsufficientBalance, SameAccountTransfer
from models import AccountStatus, TransactionType
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

        if account.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_key)

        self.account_repository.register_transaction(account, TransactionType.WITHDRAW, amount)

        self.session.commit()
        return accountDTO.only_obj_key(account)

    def transfer(self, account_from_key: str, account_to_key: str, amount: float):
        if amount <= 0:
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
                raise InsufficientBalance(account_from_key, amount, account_from.balance)

        self.account_repository.register_transfer(account_from, account_to, amount)
        self.session.commit()
        return accountDTO.only_obj_key(account_from)

    def extract(self, account_key: str):
        account = self.account_repository.get_by_key_for_update(account_key)

        if account is None:
            raise NotFoundAccount(account_key)

        extract = self.account_repository.get_extract(account)
        return accountDTO.list_extract_to_list_dict(extract)