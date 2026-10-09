from models.base import Base
from sqlalchemy import CHAR, Column, DateTime, Integer, func

class RevokedToken(Base):
    __tablename__ = "revoked_token"

    id = Column(Integer, primary_key=True)
    jti = Column(CHAR(36), nullable=False, unique=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
