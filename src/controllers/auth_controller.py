from uuid import uuid4

import jwt
from datetime import datetime, timedelta, timezone

from controllers.base_controller import BaseController
from repositories import ClientRepository, OperatorRepository, TokenRepository
from constants import JWT_SECRET, JWT_EXPIRATION_MINUTES
from errors import InvalidCredentials
from dtos import authDTO

class AuthController(BaseController):
    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context)
        self.operator_repository = OperatorRepository(self.context)
        self.token_repository = TokenRepository(self.context)

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


    def logout(self) -> dict:
        jti = self.context.authenticated_jti
        exp = self.context.authenticated_exp
        self.token_repository.revoke(jti, datetime.fromtimestamp(exp, tz=timezone.utc))
        self.session.commit()
        return authDTO.only_obj_message()


    def _generate_token(self, subject_key: str, token_type: str) -> dict:
        payload = {
            "subject_key": subject_key,
            "type": token_type,
            "jti" : str(uuid4()),
            "exp": datetime.now(timezone.utc) + timedelta(minutes=JWT_EXPIRATION_MINUTES), 
        }

        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

        return authDTO.only_obj_token(token)