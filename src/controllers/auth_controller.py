import jwt
from datetime import datetime, timedelta, timezone

from controllers.base_controller import BaseController
from repositories import ClientRepository, OperatorRepository
from constants import JWT_SECRET, JWT_EXPIRATION_MINUTES
from errors import InvalidCredentials

class AuthController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context)
        self.operator_repository = OperatorRepository(self.context)

    def login_client(self, document_number: str, password: str) -> dict:
        client = self.client_repository.get_by_document_number(document_number)

        if client is None or not self.client_repository.check_password(client, password):
            raise InvalidCredentials()

        return self._generate_token(subject_key=client.client_key, token_type="client")

    def login_operator(self, document_number: str, password: str) -> dict:
        operator = self.operator_repository.get_by_document_number(document_number)

        if operator is None or not self.operator_repository.check_password(operator, password):
            raise InvalidCredentials()
        
        return self._generate_token(subject_key=operator.operator_key, token_type="operator")
 

    def _generate_token(self, subject_key: str, token_type: str) -> dict:
        payload = {
            "subject_key": subject_key,
            "type": token_type,
            "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES), 
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        return {"token": token}