from uuid import uuid4
from datetime import date
import os

from database import open_context, clear_context
from models import Client, ClientStatus, Account, AccountStatus
from constants import REVENUE_ACCOUNT_KEY

def seed_revenue_account():
    context = open_context()
    session = context.get_or_create_session()
    document_number = os.environ.get("ACCOUNT_DOCUMENT_NUMBER")
    password_hash = os.environ.get("ACCOUNT_PASSWORD")

    try:
        existing = session.query(Account).filter(Account.account_key == REVENUE_ACCOUNT_KEY).first()

        if existing is not None:
            print("Conta de receita já existe - nada a fazer.")
            return

        house_client = Client()
        house_client.client_key = str(uuid4())
        house_client.name = "Receita do Banco"
        house_client.email = "receita@banco.universidade"
        house_client.document_number = document_number
        house_client.birthdate = date(2000, 1, 1)
        house_client.password_hash = password_hash

        approved_status = (
            session.query(ClientStatus).filter(ClientStatus.enumerator == ClientStatus.APPROVED).one()

        )
        house_client.status = approved_status
        session.add(house_client)
        session.flush()

        active_status = (
            session.query(AccountStatus).filter(AccountStatus.enumerator == AccountStatus.ACTIVE).one()

        )

        revenue_account = Account()
        revenue_account.account_key = REVENUE_ACCOUNT_KEY
        revenue_account.client = house_client
        revenue_account.status = active_status
        revenue_account.balance = 0

        session.add(revenue_account)
        session.commit()
        print(f"Conta de receita criada: {REVENUE_ACCOUNT_KEY}")

    finally:
        session.close()
        clear_context()

if __name__ == "__main__":
    seed_revenue_account()