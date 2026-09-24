import jwt
from datetime import datetime, timedelta, timezone

from controllers.base_controller import BaseController
from repositories.client_repository import ClientRepository
from constants import JWT_SECRET, JWT_EXPIRATION_MINUTES
from errors import InvalidCredentials

class AuthController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context)

    def login(self, document_number: str, password: str) -> dict:
        client = self.client_repository.get_by_document_number(document_number)

        if client is None or not self.client_repository.check_password(client, password):
            raise InvalidCredentials

        payload = {
            "client_key": client.client_key,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES), 
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        return {"token": token}