from sqlalchemy import CHAR, Column, DateTime, ForeignKey, Integer, BigInteger, Numeric, String, UniqueConstraint, func
from sqlalchemy.orm import relationship
from models.base import Base

class CreditLine(Base):
    __tablename__ = "credit_line"

    id = Column(Integer, primary_key=True)
    credit_line_key = Column(CHAR(36), nullable=False)
    client_id = Column(Integer, ForeignKey("client.id"), nullable=False)

    approved_limit = Column(BigInteger, nullable=False)
    available_limit = Column(BigInteger, nullable=False)
    interest_rate = Column(Numeric(5, 4), nullable = False)

    status = Column(String(50), nullable=False, default="ACTIVE")
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__ = (
        UniqueConstraint("credit_line_key"),
    )

    client = relationship("Client", foreign_keys=[client_id], lazy="selectin", back_populates="credit_lines")