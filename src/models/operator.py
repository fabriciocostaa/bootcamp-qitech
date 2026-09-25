from sqlalchemy import CHAR, Column, DateTime, Integer, String, UniqueConstraint, func
from models.base import Base

class Operator(Base):
    __tablename__ = "operator"

    id = Column(Integer, primary_key=True)
    operator_key = Column(CHAR(36), nullable=False)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    document_number = Column(CHAR(14), nullable=False)
    password_hash = Column(String(255), nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())

    __table_args__= (
        UniqueConstraint("operator_key"),
        UniqueConstraint("email")
    )