from models import Operator
from uuid import uuid4
import bcrypt
from database import Context

class OperatorRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session
    
    def create_operator(self, operator_data) -> Operator:
        operator = Operator()

        operator.operator_key = str(uuid4())
        operator.email = operator_data["email"]
        operator.name = operator_data["name"]
        operator.document_number = operator_data["document_number"]
        operator.password_hash = bcrypt.hashpw(
            operator_data["password"].encode(), bcrypt.gensalt()
        ).decode()

    def get_by_document_number(self, document_number: str) -> Operator:
        return(
            self.session.query(Operator).filter(Operator.document_number == document_number).first()
        )
    
    def check_password(self, operator: Operator, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), operator.password_hash.encode())
        