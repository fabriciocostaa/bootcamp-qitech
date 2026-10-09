from abc import ABCMeta

import hashlib
import json
from database import get_context
from utils.logger import get_logger
from errors import OperatorRequired, IdempotencyKeyConflict

class BaseController(metaclass=ABCMeta):
    """O que todo controller tem em comum: a conexão com o banco e o log.

    Nada chega por parâmetro: o controller pega o CONTEXTO da requisição
    em que está rodando. Quem preparou esse contexto foi o middleware.

    Guardar o `self.context`, e não só a sessão, é o que permite o
    repository receber `context` em vez de `db`: o contexto é a coisa que
    viaja entre as camadas, e a sessão é só o que ele carrega hoje.

    É aqui que a sessão nasce, no `get_or_create_session` — construir um
    controller é a mesma coisa que dizer "eu uso banco".
    """

    def __init__(self, class_name: str) -> None:
        self.context = get_context()
        self.session = self.context.get_or_create_session()
        self.logger = get_logger(class_name)

    def require_operator(self) -> None:
        if self.context.authenticated_operator_key is None:
            raise OperatorRequired()

    def operator_key(self) -> str:
        return self.context.authenticated_operator_key

    def _hash_request(self, **fields) -> str:
        raw = json.dumps(fields, sort_keys=True, default=str)
        return hashlib.sha256(raw.encode()).hexdigest()

    def _check_idempotency(self, idempotency_key: str, endpoint: str, request_hash: str):
        if idempotency_key is None:
            return None

        existing = self.idempotency_repository.get_by_key(idempotency_key, endpoint)

        if existing is None:
            return None

        if existing.request_hash != request_hash:
            raise IdempotencyKeyConflict(idempotency_key)

        return existing.response_body