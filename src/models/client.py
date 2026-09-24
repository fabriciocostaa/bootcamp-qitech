from sqlalchemy import CHAR, Column, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint, func, VARCHAR
from sqlalchemy.orm import relationship
from models.base import Base
from models import ClientStatus


class Client(Base):
    __tablename__ = "client"

    id = Column(Integer, primary_key=True)
    client_key = Column(CHAR(36), nullable=False)
    status_id = Column(Integer, ForeignKey(ClientStatus.id), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    document_number = Column(CHAR(14), nullable=False)
    password_hash = Column(VARCHAR(255), nullable=False)
    birthdate = Column(Date, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("client_key"),
        UniqueConstraint("document_number"),
        UniqueConstraint("email"),
    )

    status = relationship("ClientStatus", foreign_keys=[status_id], lazy="selectin")

    accounts = relationship("Account", back_populates="client")

    status_events = relationship(
    "ClientStatusEvent",
    back_populates="client",
    order_by="asc(ClientStatusEvent.event_datetime)",
    )