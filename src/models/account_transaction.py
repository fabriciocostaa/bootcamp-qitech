# src/models/account_transaction.py
from sqlalchemy import BigInteger, Column, ForeignKey, Integer, Numeric, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Account, TransactionType


class AccountTransaction(Base):
    __tablename__ = "account_transaction"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    type_id = Column(Integer, ForeignKey(TransactionType.id), nullable=False)
    amount = Column(BigInteger, nullable=False)
    fee = Column(BigInteger, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    # Chave estrangeira para a mesma tabela
    related_transaction_id = Column(Integer, ForeignKey("account_transaction.id"), nullable=True)

    account = relationship("Account", foreign_keys=[account_id], lazy="selectin")
    type = relationship("TransactionType", foreign_keys=[type_id], lazy="selectin")

    # Acessa a transação pai/original
    related_transaction = relationship(
        "AccountTransaction", 
        remote_side=[id],
        backref="subsequent_transactions"
    )