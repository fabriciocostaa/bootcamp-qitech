class authDTO:
    @staticmethod
    def only_obj_token(token: str) -> dict:
        dto = dict()
        dto["token"] = token

        return dto

    
    @staticmethod
    def only_obj_message() -> dict:
        return {"message": "logout successful."}