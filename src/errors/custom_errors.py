from errors import QIException


class NotFoundSampleEntity(QIException):
    code = "QIT001001"

    def __init__(self, sample_entity_key) -> None:
        title = "Entity not Found"
        http_status = 404
        description = f"Entity with key {sample_entity_key} was not found."
        translation = f"A entidade com chave {sample_entity_key} não foi encontrada."
        super().__init__(title, self.code, http_status, description, translation)


class SampleEntityFinalStatus(QIException):
    code = "QIT001002"

    def __init__(self, old_status, new_status) -> None:
        title = "Entity cannot change status"
        http_status = 409
        description = f"Entity with status {old_status} cannot update to {new_status}."
        translation = "Essa entidade não pode ser atualizada."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidDocumentNumber(QIException):
    """O CPF tem o formato certo e não existe.

    422, e não 400, de propósito: 400 quer dizer "não consegui ler o seu
    pedido". Aqui a API leu, entendeu, e o valor é que não pode existir —
    os dois últimos dígitos não batem com a conta. A diferença está
    explicada em src/utils/document_number.py.
    """

    code = "QIT001003"

    def __init__(self, document_number) -> None:
        title = "Invalid Document Number"
        http_status = 422
        description = f"The document number {document_number} is not a valid CPF."
        translation = "O CPF informado não é válido."
        super().__init__(title, self.code, http_status, description, translation)


class DuplicatedDocumentNumber(QIException):
    """Já existe um cadastro com este CPF.

    409 Conflict: o pedido está correto em si, e o que impede é o que já
    está no banco. É a mesma família do SampleEntityFinalStatus aqui em
    cima — conflito com o que já existe, não erro de quem pediu.
    """

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


class UnderageSampleEntity(QIException):
    code = "QIT001006"

    def __init__(self, age, minimum_age) -> None:
        title = "Entity is underage"
        http_status = 422
        description = f"The entity is {age} years old, and the minimum is {minimum_age}."
        translation = f"É preciso ter pelo menos {minimum_age} anos."
        super().__init__(title, self.code, http_status, description, translation)


class InvalidBirthdate(QIException):
    """A data tem o formato certo e não existe no calendário.

    Existe porque o `pattern` do schema sabe contar dígitos, não dias:
    "2025-02-30" e "9999-99-99" passam pelo regex e morrem no
    `date.fromisoformat`. Sem esta classe, esse ValueError virava 500 —
    a API culpando a si mesma por um erro de quem chamou.
    """

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
    """A conta existe, mas não está em estado de receber movimentação."""

    code = "QIT002002"

    def __init__(self, account_key) -> None:
        title = "Account is not active"
        http_status = 409
        description = f"Account with key {account_key} is not active."
        translation = f"Essa conta com chave {account_key} não está ativa."
        super().__init__(title, self.code, http_status, description, translation)


class InsufficientBalance(QIException):
    """Formato certo, valor possível — só não cabe no saldo atual.

    422, mesma lógica do InvalidDocumentNumber: não é "não entendi o
    pedido", é "entendi, e não pode ser atendido do jeito que está".
    """

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

    def __init__(self, start_date, end_date) -> None:
        title = "Invalid Date"
        http_status = 422
        description = f"start_date ({start_date}) is after end_date ({end_date})"
        translation = f"A data de início ({start_date}) é posterior à data de término ({end_date})."
        super().__init__(title, self.code, http_status, description, translation)