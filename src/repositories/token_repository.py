from datetime import datetime
from database import Context
from models import RevokedToken

class TokenRepository:
    def __init__(self, context: Context) -> None:
        self.session = context.get_or_create_session()

    def revoke(self, jti: str, expires_at: datetime) -> None:
        revoked_token = RevokedToken()
        revoked_token.jti = jti
        revoked_token.expires_at = expires_at
        self.session.add(revoked_token)

    def is_revoked(self, jti: str) -> bool:
        return self.session.query(RevokedToken).filter(RevokedToken.jti == jti).first() is not None