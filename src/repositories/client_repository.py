from datetime import date, datetime
from uuid import uuid4
import bcrypt
from sqlalchemy import func

from database import Context
from models import Client, ClientStatus, ClientStatusEvent

class ClientRepository:

    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def create(self, client_data: dict) -> Client:
        client = Client()

        client.client_key = str(uuid4())
        client.status = self.get_status(ClientStatus.PENDING)
        client.name = client_data["name"]
        client.email = client_data["email"]
        client.document_number = client_data["document_number"]
        client.password_hash = bcrypt.hashpw(
            client_data["password"].encode(), bcrypt.gensalt()
        ).decode()
        client.birthdate = date.fromisoformat(client_data["birthdate"])

        client.status_events.append(ClientStatusEvent(
            status=client.status,
            event_datetime=datetime.now()
        ))
        self.session.add(client)
        return client

    def update_status(self, client: Client, new_status_enumerator: str, operator=None) -> None:
        new_status = self.get_status(new_status_enumerator)
        client.status = new_status

        new_status_event = ClientStatusEvent()
        new_status_event.status = new_status

        if operator:
            new_status_event.operator_id = operator.id
        
        new_status_event.event_datetime = datetime.now()

        client.status_events.append(new_status_event)

    def check_password(self, client: Client, password: str) -> bool:
        return bcrypt.checkpw(password.encode(), client.password_hash.encode())

    def get_by_key(self, client_key: str) -> Client:
        return self.session.query(Client).filter(Client.client_key == client_key).first()

    def get_by_document_number(self, document_number: str) -> Client:
        return self.session.query(Client).filter(Client.document_number == document_number).first()

    def get_by_email(self, email: str) -> Client:
        return self.session.query(Client).filter(func.lower(Client.email) == email.lower()).first()

    def get_status(self, enumerator: str) -> ClientStatus:
        return self.session.query(ClientStatus).filter(ClientStatus.enumerator == enumerator).one()

    def list_page(self, limit: int, offset: int, filters: dict) -> list:
        query = self.session.query(Client)

        status_enumerators = filters.get("status_enumerators")
        if status_enumerators:
            query = query.join(Client.status).filter(ClientStatus.enumerator.in_(status_enumerators))

        name = filters.get("name")
        if name is not None:
            name = name.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            query = query.filter(Client.name.ilike(f"%{name}%", escape="\\"))

        email = filters.get("email")
        if email is not None:
            query = query.filter(func.lower(Client.email) == email.lower())

        document_number = filters.get("document_number")
        if document_number is not None:
            query = query.filter(Client.document_number == document_number)

        birthdate_from = filters.get("birthdate_from")
        if birthdate_from is not None:
            query = query.filter(Client.birthdate >= birthdate_from)

        birthdate_to = filters.get("birthdate_to")
        if birthdate_to is not None:
            query = query.filter(Client.birthdate <= birthdate_to)

        query = query.order_by(Client.created_at.desc(), Client.id.desc())

        return query.limit(limit + 1).offset(offset).all()
