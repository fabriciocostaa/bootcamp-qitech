from database import Context
from models import IdempotencyKey

class IdempotencyRepository:
    def __init__(self, context) -> None:
        self.session = context.db_session

    def get_by_key(self, idempotency_key: str, endpoint: str) -> IdempotencyKey:
        return (
            self.session.query(IdempotencyKey)
            .filter(
                IdempotencyKey.idempotency_key == idempotency_key,
                IdempotencyKey.endpoint == endpoint
            ).one_or_none()
        )

    def create(self, idempotency_key: str, endpoint: str, request_hash: str, response_body: dict) -> IdempotencyKey:
        record = IdempotencyKey()
        record.idempotency_key = idempotency_key
        record.endpoint = endpoint
        record.request_hash = request_hash
        record.response_body = response_body

        self.session.add(record)
        return record