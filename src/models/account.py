from sqlalchemy import CHAR, Column, BigInteger, DateTime, ForeignKey, Integer, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Client, AccountStatus


class Account(Base):
    __tablename__ = "account"

    id = Column(Integer, primary_key=True)
    account_key = Column(CHAR(36), nullable=False)
    balance = Column(BigInteger, nullable=False, default=0)
    client_id = Column(Integer, ForeignKey(Client.id), nullable=False)
    status_id = Column(Integer, ForeignKey(AccountStatus.id), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("account_key"),)

    client = relationship("Client", foreign_keys=[client_id], back_populates="accounts", lazy="selectin")
    status = relationship("AccountStatus", foreign_keys=[status_id], lazy="selectin")

    status_events = relationship(
        "AccountStatusEvent",
        back_populates="account",
        order_by="asc(AccountStatusEvent.event_datetime)",
    )