from sqlalchemy import Column, DateTime, Integer, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB
from models.base import Base

class IdempotencyKey(Base):
    __tablename__ = "idempotency_key"

    id = Column(Integer, primary_key=True)
    idempotency_key = Column(String(255), nullable=False)
    endpoint = Column(String(255), nullable=False)
    request_hash = Column(String(64), nullable=False)
    response_body = Column(JSONB, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (UniqueConstraint("idempotency_key", "endpoint"),)