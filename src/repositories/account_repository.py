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

    def register_transaction(self, account: Account, type_enumerator:str, amount: int) -> None:
        transaction_type = (
            self.session.query(TransactionType)
            .filter(TransactionType.enumerator == type_enumerator)
            .one()
        )

        transaction = AccountTransaction()
        transaction.account = account
        transaction.type = transaction_type
        transaction.amount = amount

        if type_enumerator == TransactionType.DEPOSIT:
            account.balance += amount

        elif type_enumerator == TransactionType.WITHDRAW:
            account.balance -= amount

        self.session.add(transaction)