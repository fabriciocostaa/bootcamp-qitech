from database import Context
from models import Client, Account, AccountStatus, AccountStatusEvent, TransactionType, AccountTransaction, AccountOperation, OperationKind
from datetime import datetime, time
from uuid import uuid4

class AccountRepository:

    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, client: Client) -> Account:
        account = Account()

        account.account_key = str(uuid4())
        account.balance = 0
        account.client = client
        account.status = self.get_status(AccountStatus.ACTIVE)

        first_event = AccountStatusEvent()
        first_event.status = account.status
        first_event.event_datetime = datetime.now()
        account.status_events.append(first_event)

        self.session.add(account)
        return account

    def get_operation_by_idempotency(self, actor_client_id: int, idempotency_key: str) -> AccountOperation:
        return (
            self.session.query(AccountOperation)
            .filter(
                AccountOperation.actor_client_id == actor_client_id,
                AccountOperation.idempotency_key == idempotency_key,
            )
            .one_or_none()
        )

    def get_status(self, enumerator: str) -> AccountStatus:
        return self.session.query(AccountStatus).filter(AccountStatus.enumerator == enumerator).one()

    def update_status(self, account: Account, new_status_enumerator: str, operator=None) -> None:
        new_status = self.get_status(new_status_enumerator)
        account.status = new_status

        new_status_event = AccountStatusEvent()
        new_status_event.status = new_status

        if operator:
            new_status_event.operator_id = operator.id

        new_status_event.event_datetime = datetime.now()

        account.status_events.append(new_status_event)

    def get_by_key_for_update(self, account_key: str) -> Account:
        return (
            self.session.query(Account)
            .filter(Account.account_key == account_key)
            .with_for_update()
            .one_or_none()
        )

    def get_by_key(self, account_key: str) -> Account:
        return(
            self.session.query(Account)
            .filter(Account.account_key == account_key)
            .first()
        )

    def create_operation(
        self, actor_client, kind_enumerator: str, amount: int, fee: int,
        origin_account=None, target_account=None,
        idempotency_key: str = None, request_hash: str = None,
        ) -> AccountOperation:
        
        kind = self.session.query(OperationKind).filter(OperationKind.enumerator == kind_enumerator).one()

        operation = AccountOperation()
        operation.operation_key = str(uuid4())
        operation.actor = actor_client
        operation.kind = kind
        operation.origin_account = origin_account
        operation.target_account = target_account
        operation.amount = amount
        operation.fee = fee
        operation.idempotency_key = idempotency_key
        operation.request_hash = request_hash

        self.session.add(operation)
        self.session.flush()
        return operation

    def get_transaction_type(self, enumerator: str) -> TransactionType:
            return self.session.query(TransactionType).filter(TransactionType.enumerator == enumerator).one()

    def register_transaction(
        self, operation: AccountOperation, account: Account, type_enumerator: str,
        amount: int, related_transaction_id: int = None,
        ) -> AccountTransaction:
        
        transaction_type = self.get_transaction_type(type_enumerator)

        transaction = AccountTransaction()
        transaction.operation = operation
        transaction.account = account
        transaction.type = transaction_type
        transaction.amount = amount
        transaction.related_transaction_id = related_transaction_id

        if type_enumerator in (TransactionType.DEPOSIT, TransactionType.TRANSFER_IN, TransactionType.FEE_CREDIT):
            account.balance += amount
        else:
            account.balance -= amount

        self.session.add(transaction)
        self.session.flush()
        return transaction

    def get_accounts_for_update(self, *account_keys: str) -> dict[str, Account]:
        ordered_keys = sorted(set(account_keys))
        accounts = {}

        for key in ordered_keys:
            accounts[key] = self.get_by_key_for_update(key)

        return accounts

    def register_transfer(
        self, from_account: Account, to_account: Account, revenue_account: Account,
        amount: int, fee: int
    ) -> None:
        transfer_out = self.get_transaction_type(TransactionType.TRANSFER_OUT)
        transfer_in = self.get_transaction_type(TransactionType.TRANSFER_IN)

        out_transaction = AccountTransaction()
        out_transaction.account = from_account
        out_transaction.type = transfer_out
        out_transaction.amount = amount
        from_account.balance -= amount
        self.session.add(out_transaction)
        self.session.flush()

        in_transaction = AccountTransaction()
        in_transaction.account = to_account
        in_transaction.type = transfer_in
        in_transaction.amount = amount
        in_transaction.related_transaction_id = out_transaction.id
        to_account.balance += amount
        self.session.add(in_transaction)
        self.session.flush()

        out_transaction.related_transaction_id = in_transaction.id

        if fee > 0:
            fee_debit_type = self.get_transaction_type(TransactionType.FEE_DEBIT)
            fee_credit_type = self.get_transaction_type(TransactionType.FEE_CREDIT)

            fee_debit = AccountTransaction()
            fee_debit.account = from_account
            fee_debit.type = fee_debit_type
            fee_debit.amount = fee
            from_account.balance -= fee
            self.session.add(fee_debit)
            self.session.flush()

            fee_credit = AccountTransaction()
            fee_credit.account = revenue_account
            fee_credit.type = fee_credit_type
            fee_credit.amount = fee
            fee_credit.related_transaction_id = fee_debit.id
            revenue_account.balance += fee
            self.session.add(fee_credit)
            self.session.flush()

            fee_debit.related_transaction_id = fee_credit.id

    def list_page(self, account: Account, limit: int, offset: int, filters: dict) -> list[AccountTransaction]:
        query = self.session.query(AccountTransaction).filter(AccountTransaction.account == account)

        
        start_date = filters.get("start_date")
        if start_date is not None:
            query = query.filter(AccountTransaction.created_at >= start_date)

        end_date = filters.get("end_date")
        if end_date is not None:
            query = query.filter(AccountTransaction.created_at <= datetime.combine(end_date, time.max))

        query = query.order_by(AccountTransaction.created_at.desc())
        return query.offset(offset).limit(limit).all()

    def get_by_client_id_for_update(self, client_id: int) -> Account:
        return (
            self.session.query(Account)
            .filter(Account.client_id == client_id)
            .with_for_update()
            .populate_existing()
            .one_or_none()
        )