from models import Account

class accountDTO:

    @staticmethod
    def only_obj_key(account: Account) -> dict:
        dto = dict()
        dto["account_key"] = account.account_key

        return dto
