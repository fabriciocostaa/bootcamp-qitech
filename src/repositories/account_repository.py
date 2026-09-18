from database import Context
from models import Client, Account, AccountStatus, AccountStatusEvent
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