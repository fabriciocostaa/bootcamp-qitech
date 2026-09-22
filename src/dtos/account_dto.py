from models import Account

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
                "created_at": transaction.created_at.isoformat(),
            }
            extract_list.append(transaction_dict)
        return extract_list