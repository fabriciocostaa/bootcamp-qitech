from sqlalchemy import Column, Integer, UniqueConstraint, String
from models.base import Base

class TransactionType(Base):
    __tablename__ = "transaction_type"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)

    __table_args__ = (UniqueConstraint("enumerator"),)

    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"