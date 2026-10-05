from sqlalchemy import Column, Integer, String, UniqueConstraint
from models.base import Base

class OperationKind(Base):
    __tablename__ = "operation_kind"

    id = Column(Integer, primary_key=True)
    enumerator = Column(String(50), nullable=False)

    __table_args__ = (UniqueConstraint("enumerator"),)

    DEPOSIT = "deposit"
    WITHDRAW = "withdraw"
    TRANSFER = "transfer"