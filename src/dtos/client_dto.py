from copy import deepcopy
from typing import List

from models import Client


class clientDTO:

    @staticmethod
    def obj_to_dict(client: Client) -> dict:
        client_dto = clientDTO.obj_to_simplified_dict(client)

        for status_event in client.status_events:
            status_event_dto = dict()
            status_event_dto["status"] = status_event.status.enumerator

            if status_event.operator:
                status_event_dto["operator_key"] = status_event.operator.operator_key
            
            status_event_dto["event_datetime"] = status_event.event_datetime.isoformat()

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

    @staticmethod
    def status_history_to_list(status_events: list) -> list:
        history = {"status_events": []}
        for event in status_events:
            history["status_events"].append({
                "status": event.status.enumerator,
                "event_datetime": event.event_datetime.isoformat(),
                "operator_key": event.operator.operator_key if getattr(event, "operator", None) else None
            })
        return history
