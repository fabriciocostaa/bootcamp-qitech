import os
from  connectors.rest_connector import RestConnector

class KYCConnector(RestConnector):
    def __init__(self):
        super().__init__(
            class_name=self.__class__.__name__,
            base_url=os.getenv("KYC_API_URL", "http://mock-server:8080"),
            timeout=int(os.getenv("API_TIMEOUT", "5")),
            internal_token=os.getenv("INTERNAL_TOKEN", "mock-token")
        )

    def verify_identity(self, cpf: str, full_name: str):
        # envia dados de identidade
        return self.send(
            endpoint="/kyc/verify",
            method="POST",
            payload={"cpf": cpf, "full_name": full_name}
        )