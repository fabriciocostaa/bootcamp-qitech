import os
import bcrypt

from database import get_context, open_context, clear_context
from models import Operator

def seed_admin():
    document_number = os.environ.get("ADMIN_DOCUMENT_NUMBER")
    password = os.environ.get("ADMIN_INITIAL_PASSWORD")

    if not document_number or not password:
        print("ADMIN_DOCUMENT_NUMBER / ADMIN_INITIAL_PASSWORD não definidos")
        return

    context = open_context()
    session = context.get_or_create_session()

    try:
        existing = session.query(Operator).filter(Operator.document_number == document_number).first()
        if existing is not None:
            print(f"Admin {document_number} já existe - nada a fazer")
            return

        from uuid import uuid4

        operator = Operator()
        operator.operator_key = str(uuid4())
        operator.name = "Admin"
        operator.email = "admin@example.com"
        operator.document_number = document_number
        operator.password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

        session.add(operator)
        session.commit()
        print(f"Admin criado com sucesso")

    finally:
        session.close()
        clear_context()

if __name__ == "__main__":
    seed_admin()