from database import Context
from models import Client, Account, AccountStatus, AccountStatusEvent, TransactionType, AccountTransaction
from datetime import datetime
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

        # Mesma lógica que já vale pra cliente: o primeiro status
        # também é um evento — o histórico começa completo, sem
        # buraco entre "quando a conta nasceu" e a primeira mudança.
        first_event = AccountStatusEvent()
        first_event.status = account.status
        first_event.event_datetime = datetime.now()
        account.status_events.append(first_event)

        self.session.add(account)
        return account


    def get_status(self, enumerator: str) -> AccountStatus:
        return self.session.query(AccountStatus).filter(AccountStatus.enumerator == enumerator).one()

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

    def get_transaction_type(self, enumerator: str) -> TransactionType:
            return self.session.query(TransactionType).filter(TransactionType.enumerator == enumerator).one()

    def register_transaction(self, account: Account, type_enumerator:str, amount: int) -> None:
        transaction_type = self.get_transaction_type(type_enumerator)

        transaction = AccountTransaction()
        transaction.account = account
        transaction.type = transaction_type
        transaction.amount = amount
        transaction.fee = 0

        if type_enumerator == TransactionType.DEPOSIT:
            account.balance += amount

        elif type_enumerator == TransactionType.WITHDRAW:
            account.balance -= amount

        self.session.add(transaction)

    def get_accounts_for_update(self, *account_keys: str) -> dict[str, Account]:
        """Trava N contas, sempre na mesma ordem (por account_key),
        pra evitar deadlock entre operações concorrentes que envolvem
        as mesmas contas em ordens diferentes.
        """
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

        # A tarifa só existe se fee > 0 — transferência sem custo não
        # deveria gerar lançamento nenhum de taxa, nem de valor zero.
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
            query = query.filter(AccountTransaction.created_at <= end_date)

        query = query.order_by(AccountTransaction.created_at.desc())
        return query.offset(offset).limit(limit).all()