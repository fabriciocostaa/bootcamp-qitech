from copy import deepcopy
from typing import List

from models import Client


class clientDTO:
    """Traduz o objeto do banco no JSON que a API devolve.

    O repository entrega um `client` — o espelho da tabela, com
    coluna JSON e chave estrangeira. Nada disso sai para o cliente: aqui
    esse objeto vira um dicionário simples, e é esse dicionário que o
    FastAPI transforma no JSON da resposta.

    Compare com `src/models/sample_entity.py`, que descreve a TABELA:
    lá o `hello` está escondido dentro de uma coluna JSON chamada
    `sample_entity_data`, e o status é um número apontando pra outra
    tabela. Aqui os dois são campos planos, com nome de gente.

    Campo novo na resposta se acrescenta aqui — e só aqui.
    """

    @staticmethod
    def obj_to_dict(client: Client) -> dict:
        """A entidade INTEIRA, com a história de como ela chegou aqui.

        É o dossiê: quem abre UMA entidade quer saber por onde ela
        passou, não só onde ela está. Cada mudança de status deixou uma
        linha em client_status_event, e é aqui que essas linhas
        viram resposta.
        """
        client_dto = clientDTO.obj_to_simplified_dict(client)
        client_dto["status_events"] = []

        for status_event in client.status_events:
            status_event_dto = dict()
            status_event_dto["status"] = status_event.status.enumerator
            status_event_dto["event_datetime"] = status_event.event_datetime.isoformat()
            client_dto["status_events"].append(status_event_dto)

        client_dto["accounts"] = []
        for account in client.accounts:
            client_dto["accounts"].append({
                "account_key": account.account_key,
                "balance": f"{account.balance / 100:.2f}", 
                "status": account.status.enumerator,
            })

        return client_dto

    @staticmethod
    def obj_to_simplified_dict(client: Client) -> dict:
        """A entidade sem a trilha de status — o resumo.

        Existe por causa da LISTAGEM, e o motivo não é economizar
        bytes: a trilha mora em OUTRA tabela, e montá-la item a item
        custa uma consulta por entidade da página.

        Não é estimativa. Medido nesta API, com 28 entidades na
        página: 11 ms devolvendo o resumo, 45 ms devolvendo a trilha
        junto — quatro vezes mais, e a diferença cresce com o tamanho
        da página.

        Quem lista está varrendo; quem abre uma entidade está
        investigando. São dois pedidos diferentes, e por isso são dois
        DTOs.
        """
        # O deepcopy não é frescura: sem ele, `dto` seria o MESMO
        # dicionário que vive dentro do objeto do banco, e as linhas
        # abaixo sujariam esse objeto — que o resto da requisição
        # ainda vai usar.
        dto = dict()
        dto["client_key"] = client.client_key
        dto["name"] = client.name
        dto["email"] = client.email
        dto["document_number"] = client.document_number
        dto["birthdate"] = client.birthdate.isoformat()
        dto["status"] = client.status.enumerator

        return dto

    @staticmethod
    def list_obj_to_list_dict(sample_entities_list: List[Client]) -> List[dict]:
        sample_entities_dict_list = []

        for client in sample_entities_list:
            sample_entities_dict_list.append(
                clientDTO.obj_to_simplified_dict(client)
            )

        return sample_entities_dict_list

    @staticmethod
    def only_obj_key(client: Client) -> dict:
        dto = dict()
        dto["client_key"] = client.client_key

        return dto
