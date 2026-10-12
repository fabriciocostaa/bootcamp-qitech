from sqlalchemy import BigInteger, Column, ForeignKey, Integer, Numeric, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Account, TransactionType


class AccountTransaction(Base):
    __tablename__ = "account_transaction"

    id = Column(Integer, primary_key=True)
    operation_id = Column(Integer, ForeignKey("account_operation.id"), nullable=False)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    type_id = Column(Integer, ForeignKey(TransactionType.id), nullable=False)
    amount = Column(BigInteger, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    related_transaction_id = Column(Integer, ForeignKey("account_transaction.id"), nullable=True)

    account = relationship("Account", foreign_keys=[account_id], lazy="selectin")
    type = relationship("TransactionType", foreign_keys=[type_id], lazy="selectin")
    operation = relationship("AccountOperation", back_populates="transactions", lazy="selectin")

    related_transaction = relationship(
        "AccountTransaction", 
        remote_side=[id],
        backref="subsequent_transactions"
    )