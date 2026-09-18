from sqlalchemy import Column, ForeignKey, Integer, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Account, AccountStatus


class AccountStatusEvent(Base):
    __tablename__ = "account_status_event"

    id = Column(Integer, primary_key=True)
    account_id = Column(Integer, ForeignKey(Account.id), nullable=False)
    status_id = Column(Integer, ForeignKey(AccountStatus.id), nullable=False)
    event_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    account = relationship(
        "Account",
        foreign_keys=[account_id],
        back_populates="status_events",
        lazy="selectin",
    )
    status = relationship("AccountStatus", foreign_keys=[status_id], lazy="selectin")