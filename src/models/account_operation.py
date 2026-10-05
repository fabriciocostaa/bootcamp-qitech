from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, BigInteger, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Client, OperationKind, Account


class AccountOperation(Base):
    __tablename__ = "account_operation"

    id = Column(Integer, primary_key=True)
    operation_key = Column(CHAR(36), nullable=False)
    actor_client_id = Column(Integer, ForeignKey(Client.id), nullable=False)
    kind_id = Column(Integer, ForeignKey(OperationKind.id), nullable=False)
    origin_account_id = Column(Integer, ForeignKey(Account.id), nullable=True)
    target_account_id = Column(Integer, ForeignKey(Account.id), nullable=True)
    amount = Column(BigInteger, nullable=False)
    fee = Column(BigInteger, nullable=False, default=0)
    idempotency_key = Column(String(255), nullable=False)
    request_hash = Column(String(64), nullable=True)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("operation_key"),
        UniqueConstraint("actor_client_id", "idempotency_key"),
    )

    actor = relationship("Client", foreign_keys=[actor_client_id], lazy="selectin")
    kind = relationship("OperationKind", foreign_keys=[kind_id], lazy="selectin")
    origin_account = relationship("Account", foreign_keys=[origin_account_id], lazy="selectin")
    target_account = relationship("Account", foreign_keys=[target_account_id], lazy="selectin")

    transactions = relationship("AccountTransaction", back_populates="operation")