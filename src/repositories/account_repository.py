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

    def get_transaction_type(self, enumerator: str) -> TransactionType:
            return self.session.query(TransactionType).filter(TransactionType.enumerator == enumerator).one()

    def register_transaction(self, account: Account, type_enumerator:str, amount: int) -> None:
        transaction_type = self.get_transaction_type(type_enumerator)

        transaction = AccountTransaction()
        transaction.account = account
        transaction.type = transaction_type
        transaction.amount = amount

        if type_enumerator == TransactionType.DEPOSIT:
            account.balance += amount

        elif type_enumerator == TransactionType.WITHDRAW:
            account.balance -= amount

        self.session.add(transaction)

    def get_two_by_key_for_update(self, account_key1: str, account_key2: str) -> tuple[Account, Account]:
        first_key, second_key = sorted([account_key1, account_key2])

        first_account = self.get_by_key_for_update(first_key) #retorna a conta com a chave menor, para evitar deadlocks
        second_account = self.get_by_key_for_update(second_key)

        accounts_by_key = {first_key: first_account, second_key: second_account}
        return accounts_by_key[account_key1], accounts_by_key[account_key2] #retorna as contas na ordem das chaves passadas, para não quebrar a lógica do controller

    def register_transfer(self, account_from: Account, account_to: Account, amount: int) -> None:
        transfer_in_type = self.get_transaction_type(TransactionType.TRANSFER_IN)
        transfer_out_type = self.get_transaction_type(TransactionType.TRANSFER_OUT)

        transaction_out = AccountTransaction()
        transaction_out.account = account_from
        transaction_out.type = transfer_out_type
        transaction_out.amount = amount
        account_from.balance -= amount
        self.session.add(transaction_out)
        self.session.flush()  # precisa do id antes de linkar a outra ponta

        transaction_in = AccountTransaction()
        transaction_in.account = account_to
        transaction_in.type = transfer_in_type
        transaction_in.amount = amount
        transaction_in.related_transaction_id = transaction_out.id 
        account_to.balance += amount
        self.session.add(transaction_in)
        self.session.flush()  # garante que as duas transações sejam persistidas antes de continuar

        transaction_out.related_transaction_id = transaction_in.id # Linka as duas transações