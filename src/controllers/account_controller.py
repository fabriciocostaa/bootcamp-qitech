from controllers.base_controller import BaseController
from repositories import AccountRepository, ClientRepository, OperatorRepository
from errors import NotFoundAccount, InvalidAmount, AccountNotActive, InsufficientBalance, SameAccountTransfer, InvalidDate, AccountNotOwnedByClient, IdempotencyKeyConflict, AccountInvalidStatus
from models import AccountStatus, TransactionType, Account, OperationKind
from datetime import date
from dtos.account_dto import accountDTO
from sqlalchemy.exc import IntegrityError
from constants import REVENUE_ACCOUNT_KEY
from utils.fee import calculate_transfer_fee

class AccountController(BaseController):
    def __init__(self) ->None:
        super().__init__(__name__)
        self.account_repository = AccountRepository(self.context) 
        self.client_repository = ClientRepository(self.context)
        self.operator_repository = OperatorRepository(self.context)

    def get_status_history(self, account_key: str) -> dict:
        self.logger.debug(f"Buscando histórico da conta {account_key}")

        account = self.account_repository.get_by_key(account_key)
        if account is None:
            raise NotFoundAccount(account_key)

        self.require_operator() 

        response = accountDTO.status_history_to_list(account.status_events)

        return response

    def _check_account_ownership(self, account: Account) -> None:
        if account.client.client_key != self.context.authenticated_client_key:
            raise AccountNotOwnedByClient()
    
    def deposit(self, account_key: str, amount: float, idempotency_key: str = None):
        if amount <= 0:
            raise InvalidAmount(amount)
        
        actor = self.client_repository.get_by_key(self.context.authenticated_client_key)
        if actor is None:
            raise AccountNotOwnedByClient()
        self.session.refresh(actor, with_for_update={"key_share": True})
        request_hash = self._hash_request(account_key=account_key, amount=amount)

        account = self.account_repository.get_by_key_for_update(account_key)

        if account is None:
            raise NotFoundAccount(account_key)
        
        self._check_account_ownership(account)

        operation_exist = self.account_repository.get_operation_by_idempotency(actor.id, idempotency_key)
        if operation_exist is not None:
            if operation_exist.kind.enumerator != OperationKind.DEPOSIT or operation_exist.request_hash != request_hash:
                raise IdempotencyKeyConflict(idempotency_key)
            return accountDTO.operation_to_dict(operation_exist)

        if not isinstance(amount, int):
            raise InvalidAmount(amount)

        if account.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_key)

        operation = self.account_repository.create_operation(
            actor_client=actor,
            kind_enumerator=OperationKind.DEPOSIT,
            amount=amount,
            fee=0,
            target_account=account,
            idempotency_key=idempotency_key,
            request_hash=request_hash, 
        )

        self.account_repository.register_transaction(operation, account, TransactionType.DEPOSIT, amount)

        response = accountDTO.operation_to_dict(operation)
        self.session.commit()
        return response
    
    def withdraw(self, account_key: str, amount: float, idempotency_key: str) -> dict:
        if amount <= 0:
            raise InvalidAmount(amount)

        actor = self.client_repository.get_by_key(self.context.authenticated_client_key)
        if actor is None:
            raise AccountNotOwnedByClient()
        self.session.refresh(actor, with_for_update={"key_share": True})
        request_hash = self._hash_request(account_key=account_key, amount=amount)

        account = self.account_repository.get_by_key_for_update(account_key)

        if account is None:
            raise NotFoundAccount(account_key)

        self._check_account_ownership(account)

        operation_exist = self.account_repository.get_operation_by_idempotency(actor.id, idempotency_key)
        if operation_exist is not None:
            if operation_exist.kind.enumerator != OperationKind.WITHDRAW or operation_exist.request_hash != request_hash:
                raise IdempotencyKeyConflict(idempotency_key)
            return accountDTO.operation_to_dict(operation_exist)

        if not isinstance(amount, int):
            raise InvalidAmount(amount)

        if account.balance < amount:
            raise InsufficientBalance(account_key, account.balance)

        if account.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_key)

        operation = self.account_repository.create_operation(
            actor_client=actor,
            kind_enumerator=OperationKind.WITHDRAW,
            amount=amount,
            fee=0,
            target_account=account,
            idempotency_key=idempotency_key,
            request_hash=request_hash, 
        )

        self.account_repository.register_transaction(operation, account, TransactionType.WITHDRAW, amount)

        response = accountDTO.operation_to_dict(operation)
        self.session.commit()
        return response

    def transfer(self, account_from_key: str, account_to_key: str, amount: float, idempotency_key: str):
        if amount <= 0:
            raise InvalidAmount(amount)

        if not isinstance(amount, int):
            raise InvalidAmount(amount)

        if account_from_key == account_to_key:
            raise SameAccountTransfer(account_from_key)
        
        actor = self.client_repository.get_by_key(self.context.authenticated_client_key)
        if actor is None:
            raise AccountNotOwnedByClient()
        self.session.refresh(actor, with_for_update={"key_share": True})
        request_hash = self._hash_request(account_from_key=account_from_key, account_to_key=account_to_key, amount=amount)

        fee = calculate_transfer_fee(amount)
        total_debited = amount + fee

        accounts = self.account_repository.get_accounts_for_update(
        account_from_key, account_to_key, REVENUE_ACCOUNT_KEY
        )

        account_from = accounts[account_from_key]
        account_to = accounts[account_to_key]
        revenue_account = accounts[REVENUE_ACCOUNT_KEY]

        if account_from is None:
            raise NotFoundAccount(account_from_key)

        if account_to is None:
            raise NotFoundAccount(account_to_key)

        self._check_account_ownership(account_from)

        operation_exist = self.account_repository.get_operation_by_idempotency(actor.id, idempotency_key)
        if operation_exist is not None:
            if operation_exist.kind.enumerator != OperationKind.TRANSFER or operation_exist.request_hash != request_hash:
                raise IdempotencyKeyConflict(idempotency_key)
            return accountDTO.operation_to_dict(operation_exist)

        if account_from.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_from_key)

        if account_to.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive(account_to_key)

        if account_from.balance < total_debited:
            raise InsufficientBalance(account_from_key, account_from.balance)

        operation = self.account_repository.create_operation(
            actor_client=actor,
            kind_enumerator=OperationKind.TRANSFER,
            amount=amount,
            fee=fee,
            origin_account=account_from,
            target_account=account_to,
            idempotency_key=idempotency_key,
            request_hash=request_hash, 
        )

        out_tx = self.account_repository.register_transaction(operation, account_from, TransactionType.TRANSFER_OUT, amount)
        in_tx = self.account_repository.register_transaction(
        operation, account_to, TransactionType.TRANSFER_IN, amount, related_transaction_id=out_tx.id)
        
        out_tx.related_transaction_id = in_tx.id

        if fee > 0:
            fee_debit = self.account_repository.register_transaction(operation, account_from, TransactionType.FEE_DEBIT, fee)
            fee_credit = self.account_repository.register_transaction(operation, revenue_account, TransactionType.FEE_CREDIT, fee, related_transaction_id=fee_debit.id)
            fee_debit.related_transaction_id = fee_credit.id

            response = accountDTO.operation_to_dict(operation)

        try: 
            self.session.commit()
        except:
            self.session.rollback()
            existing = self.account_repository.get_operation_by_idempotency(actor.id, idempotency_key)
            return accountDTO.operation_to_dict(existing)

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

        if account.status.enumerator != AccountStatus.ACTIVE:
            raise AccountNotActive()
        
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
        try:
            return date.fromisoformat(raw_date)
        except ValueError:
            raise InvalidDate(f"Invalid date format: {raw_date}. Expected format: YYYY-MM-DD")

    def update_status(self, account_key: str, new_status: str) -> dict:
        self.require_operator() 
        
        account = self.account_repository.get_by_key_for_update(account_key)
        
        if account is None:
            raise NotFoundAccount(account_key)

        operator_key = self.operator_key()
        operator = self.operator_repository.get_by_key(operator_key) 

        self._check_status_can_change(account, new_status)

        self.account_repository.update_status(account, new_status, operator)
        self.session.commit()

        return accountDTO.only_obj_key(account)


    def _check_status_can_change(self, account: Account, new_status: str) -> None:
        old_status = account.status.enumerator
        print(old_status)

        if old_status == new_status:
            raise AccountInvalidStatus(old_status, new_status)

        if old_status == "CLOSED": 
            raise AccountInvalidStatus(old_status, new_status)
