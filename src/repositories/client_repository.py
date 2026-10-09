from datetime import date, datetime
from uuid import uuid4
import bcrypt

from database import Context
from models import Client, ClientStatus, ClientStatusEvent

class ClientRepository:
    """A camada que fala com o banco. Só aqui existe query.

    Nenhuma regra de negócio mora aqui: esta classe busca, guarda e
    atualiza — quem decide o que fazer com isso é o controller.

    Repare no que ele recebe: o CONTEXTO do trabalho, e não a sessão
    solta. A sessão é o que ele tira de lá na linha seguinte, e é tudo de
    que precisa hoje — mas a assinatura já fala a língua do que viaja
    entre as camadas. No dia em que o contexto carregar também o
    identificador da requisição, nenhum construtor daqui até o resource
    muda de forma.

    É assim nos serviços da QI, e a linha é a mesma lá e aqui:
    `self.session = context.db_session`.
    """

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
        return self.session.query(Client).filter(Client.email == email).first()

    def get_status(self, enumerator: str) -> ClientStatus:
        return self.session.query(ClientStatus).filter(ClientStatus.enumerator == enumerator).one()

    def list_page(self, limit: int, offset: int, filters: dict) -> list:
        """A pagina, estreitada por quantos filtros vierem preenchidos.

        Todo filtro segue a mesma forma: veio vazio, nao entra na query;
        veio preenchido, vira mais um `.filter()`. Como cada um deles
        acrescenta uma condicao a MESMA query, eles se somam com E — dois
        filtros sempre devolvem menos linhas que um, nunca mais.

        Repare que `ilike` e diferente de `==`: o nome casa por pedaco e
        sem ligar pra maiuscula, enquanto e-mail e CPF exigem o valor
        inteiro e exato. Essa diferenca e decisao de produto, nao detalhe
        tecnico — quem procura uma pessoa lembra meio nome, mas quem
        procura um CPF tem o CPF.

        A ordenacao no fim nao e enfeite: `limit` e `offset` recortam
        um conjunto, e um conjunto sem ordem pode voltar do banco em
        qualquer sequencia. Sem o `order_by`, a pagina 2 tem permissao
        de repetir uma linha da pagina 1 e sumir com outra. O desempate
        por `id` existe porque duas entidades podem nascer no mesmo
        instante — e ai `created_at` sozinho ainda deixaria a ordem em
        aberto.
        """
        query = self.session.query(Client)

        status_enumerators = filters.get("status_enumerators")
        if status_enumerators:
            query = query.join(Client.status).filter(ClientStatus.enumerator.in_(status_enumerators))

        name = filters.get("name")
        if name is not None:
            query = query.filter(Client.name.ilike(f"%{name}%"))

        email = filters.get("email")
        if email is not None:
            query = query.filter(Client.email == email)

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
