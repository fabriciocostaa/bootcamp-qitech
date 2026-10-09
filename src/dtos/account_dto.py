from models import Account, AccountOperation

class accountDTO:

    @staticmethod
    def only_obj_key(account: Account) -> dict:
        dto = dict()
        dto["account_key"] = account.account_key

        return dto

    @staticmethod
    def list_extract_to_list_dict(extract: list) -> list:
        extract_list = []
        for transaction in extract:
            transaction_dict = {
                "transaction_id": transaction.id,
                "account_from_key": transaction.account.account_key,
                "account_to_key": transaction.related_transaction.account.account_key if transaction.related_transaction else None,
                "type": transaction.type.enumerator,
                "amount": f"{transaction.amount/100 :.2f}",
                "fee": f"{transaction.operation.fee/100 :.2f}",
                "created_at": transaction.created_at.isoformat(),
            }
            extract_list.append(transaction_dict)
        return extract_list

    @staticmethod
    def operation_to_dict(operation: AccountOperation) -> dict:
        return {
            "operation_key": operation.operation_key,
            "kind": operation.kind.enumerator,
            "amount": f"{operation.amount/100:.2f}",
            "fee": f"{operation.fee/100:.2f}",
            "created_at": operation.created_at.isoformat(),
        }

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