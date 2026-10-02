from sqlalchemy import Column, Integer, UniqueConstraint, String
from models.base import Base

class TransactionType(Base):
    __tablename__ = "transaction_type"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)

    __table_args__ = (UniqueConstraint("enumerator"),)

    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    TRANSFER_IN = "transfer_in"
    TRANSFER_OUT = "transfer_out"
    FEE_DEBIT = "fee_debit"
    FEE_CREDIT = "fee_credit"