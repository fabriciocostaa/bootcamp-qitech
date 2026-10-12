from errors import QIException


class NotFoundClient(QIException):
    code = "QIT001001"

    def __init__(self, client_key) -> None:
        title = "Client not Found"
        http_status = 404
        description = f"The Client with key {client_key} was not found."
        translation = f"O client com chave {client_key} não foi encontrado."
        super().__init__(title, self.code, http_status, description, translation)


class ClientFinalStatus(QIException):
    code = "QIT001002"

    def __init__(self, old_status, new_status) -> None:
        title = "Client cannot change status"
        http_status = 409
        description = f"Client with status {old_status} cannot update to {new_status}."
        translation = f"Esse cliente com status {old_status} não pode atualizar para {new_status}."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDocumentNumber(QIException):

    code = "QIT001003"

    def __init__(self, document_number) -> None:
        title = "Invalid Document Number"
        http_status = 422
        description = f"The document number {document_number} is not a valid CPF."
        translation = "O CPF informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedDocumentNumber(QIException):

    code = "QIT001004"

    def __init__(self, document_number) -> None:
        title = "Document Number already registered"
        http_status = 409
        description = f"There is already an entity with the document number {document_number}."
        translation = "Já existe um cadastro com este CPF."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedEmail(QIException):
    code = "QIT001005"

    def __init__(self, email) -> None:
        title = "Email already registered"
        http_status = 409
        description = f"There is already an entity with the email {email}."
        translation = "Já existe um cadastro com este e-mail."
        super().__init__(title, self.code, http_status, description, translation)


class UnderageClient(QIException):
    code = "QIT001006"

    def __init__(self, age, minimum_age) -> None:
        title = "Client is underage"
        http_status = 422
        description = f"The Client is {age} years old, and the minimum is {minimum_age}."
        translation = f"É preciso ter pelo menos {minimum_age} anos."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidBirthdate(QIException):

    code = "QIT001007"

    def __init__(self, birthdate) -> None:
        title = "Invalid Birthdate"
        http_status = 422
        description = f"The birthdate {birthdate} is not a real date."
        translation = "A data de nascimento informada não existe."
        super().__init__(title, self.code, http_status, description, translation)

class NotFoundAccount(QIException):
    code = "QIT002001"

    def __init__(self, account_key) -> None:
        title = "Account not Found"
        http_status = 404
        description = f"Account with key {account_key} was not found."
        translation = f"A conta com chave {account_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class AccountNotActive(QIException):

    code = "QIT002002"

    def __init__(self, account_key) -> None:
        title = "Account is not active"
        http_status = 409
        description = f"Account with key {account_key} is not active."
        translation = f"Essa conta com chave {account_key} não está ativa."
        super().__init__(title, self.code, http_status, description, translation)


class InsufficientBalance(QIException):

    code = "QIT002003"

    def __init__(self, account_key, balance) -> None:
        title = "Insufficient Balance"
        http_status = 422
        description = f"Account {account_key} has only {balance/100 :.2f} available."
        translation = f"Conta {account_key} tem apenas {balance/100 :.2f} disponível."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidAmount(QIException):
    code = "QIT002004"

    def __init__(self, amount) -> None:
        title = "Invalid Amount"
        http_status = 422
        description = f"The amount {amount} is not valid."
        translation = f"O valor {amount} informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)

class SameAccountTransfer(QIException):
    code = "QIT002005"

    def __init__(self, account_key) -> None:
        title = "Same Account Transfer"
        http_status = 422
        description = f"Cannot transfer to the same account {account_key}."
        translation = f"Não é possível transferir para a mesma conta {account_key}."
        super().__init__(title, self.code, http_status, description, translation)

class InvalidDate(QIException):
    code = "QIT002006"

    def __init__(self, start_date, end_date=None) -> None:
        title = "Invalid Date"
        http_status = 422
        description = f"start_date ({start_date}) is after end_date ({end_date})"
        translation = f"A data de início ({start_date}) é posterior à data de término ({end_date})."
        if end_date is None:
            description = str(start_date)
            translation = "A data informada é inválida. Use uma data existente no formato YYYY-MM-DD."
        super().__init__(title, self.code, http_status, description, translation)

class AccountInvalidStatus(QIException):
    code = "QIT002007"

    def __init__(self, old_status, new_status) -> None:
        title = "Account cannot change status"
        http_status = 409
        description = f"Account with status {old_status} cannot update to {new_status}."
        translation = f"Essa conta com status {old_status} não pode atualizar para {new_status}."
        super().__init__(title, self.code, http_status, description, translation)

class InvalidCredentials(QIException):
    code = "QIT003001"

    def __init__(self) -> None:
        title = "Invalid Credentials"
        http_status = 401
        description = "Document number or password is incorrect."
        translation = "CPF ou senha incorretos."
        super().__init__(title, self.code, http_status, description, translation)

class UnauthorizedException(QIException):
    code = "QIT003002"

    def __init__(self) -> None:
        title = "Unauthorized"
        http_status = 401
        description = "Authentication required."
        translation = "É necessário estar autenticado."
        super().__init__(title, self.code, http_status, description, translation)

class TokenExpiredException(QIException):
    code = "QIT003003"

    def __init__(self) -> None:
        title = "Expired Token"
        http_status = 401
        description = "The token has expired."
        translation = "O token expirou."
        super().__init__(title, self.code, http_status, description, translation)

class AccountNotOwnedByClient(QIException):
    code = "QIT003005"

    def __init__(self) -> None:
        title = "Account Not Owned By Client"
        http_status = 401
        description = "The specified account does not belong to the client."
        translation = "Essa conta específica não pertence ao Cliente."
        super().__init__(title, self.code, http_status, description, translation)

class OperatorRequired(QIException):
    code = "QIT003006"

    def __init__(self) -> None:
        title = "Operator Required"
        http_status = 403
        description = "This operation requires an operator token."
        translation = "Essa operação exige um token de operador."
        super().__init__(title, self.code, http_status, description, translation)

class IdempotencyKeyConflict(QIException):
    code = "QIT003007"

    def __init__(self, idempotency_key: str) -> None:
        title = "Idempotency Key Conflict"
        http_status = 409
        description = f"Idempotency key {idempotency_key} was already used with a different request."
        translation = f"Essa chave de idempotência {idempotency_key} já foi usada em uma requisição diferente."
        super().__init__(title, self.code, http_status, description, translation),

class IdempotencyKeyMissing(QIException):
    code = "QIT003008"

    def __init__(self) -> None:
        title = "Idempotency Key Missing"
        http_status = 400
        description = "Idempotency key is required"
        translation = "É necessário informar a chave de idempotência."
        super().__init__(title, self.code, http_status, description, translation)
