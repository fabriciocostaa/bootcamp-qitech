class OperatorDTO:
    @staticmethod
    def only_obj_token(token: str) -> dict:
        dto = dict()
        dto["token"] = token

        return dto