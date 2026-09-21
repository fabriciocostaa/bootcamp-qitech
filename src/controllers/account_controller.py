from controllers.base_controller import BaseController
from repositories.account_repository import AccountRepository
from errors import NotFoundAccount, InvalidAmount, AccountNotActive  
from models import AccountStatus, TransactionType
from dtos.account_dto import accountDTO

class AccountController(BaseController):
    def __init__(self) ->None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context)

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
