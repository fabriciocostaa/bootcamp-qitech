from sqlalchemy import Column, ForeignKey, Integer, DateTime, func
from sqlalchemy.orm import relationship
from models.base import Base
from models import Client, ClientStatus


class ClientStatusEvent(Base):
    __tablename__ = "client_status_event"

    id = Column(Integer, primary_key=True)
    client_id = Column(Integer, ForeignKey(Client.id), nullable=False)
    status_id = Column(Integer, ForeignKey(ClientStatus.id), nullable=False)
    event_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    client = relationship(
        "Client",
        foreign_keys=[client_id],
        back_populates="status_events",
        lazy="selectin",
    )
    status = relationship("ClientStatus", foreign_keys=[status_id], lazy="selectin")