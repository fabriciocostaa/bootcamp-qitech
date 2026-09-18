# src/models/account_transaction.py
from sqlalchemy import Column, ForeignKey, Integer, Numeric, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Account, TransactionType


class AccountTransaction(Base):
    __tablename__ = "account_transaction"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    type_id = Column(Integer, ForeignKey(TransactionType.id), nullable=False)
    amount = Column(Numeric(15, 2), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    account = relationship("Account", foreign_keys=[account_id], lazy="selectin")
    type = relationship("TransactionType", foreign_keys=[type_id], lazy="selectin")