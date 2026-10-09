from uuid import uuid4
from database import Context
from models import CreditLine

class CreditRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, credit_data: dict) -> CreditLine:
        credit_line = CreditLine()
        
        credit_line.credit_line_key = str(uuid4())
        credit_line.client_id = credit_data["client_id"]
        credit_line.approved_limit = credit_data["approved_limit"]
        credit_line.available_limit = credit_data["available_limit"]
        credit_line.interest_rate = credit_data["interest_rate"]
        credit_line.status = "ACTIVE"
        
        self.session.add(credit_line)
        self.session.commit()
        self.session.refresh(credit_line)
        return credit_line

    def get_by_key(self, credit_line_key: str) -> CreditLine:
        return (
            self.session.query(CreditLine)
            .filter(CreditLine.credit_line_key == credit_line_key)
            .first()
        )
    
    def get_by_client_id(self, client_id: int) -> CreditLine:
        return (
            self.session.query(CreditLine)
            .filter(CreditLine.client_id == client_id)
            .first()
        )


    def deduct_limit(self, credit_line: CreditLine, amount: int) -> None:
        """Deduz o valor do limite disponível, sem fazer commit imediato."""
        credit_line.available_limit -= amount
        self.session.add(credit_line)
        self.session.flush()