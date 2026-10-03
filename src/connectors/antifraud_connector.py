import os
from  connectors.rest_connector import RestConnector

class AntifraudConnector(RestConnector):
    def __init__(self):
        super().__init__(
            class_name=self.__class__.__name__,
            base_url=os.getenv("ANTIFRAUD_API_URL", "http://mock-server:8080"),
            timeout=int(os.getenv("API_TIMEOUT", "5")),
            internal_token=os.getenv("INTERNAL_TOKEN", "mock-token")
        )

    def analyze_risk(self, cpf: str, email: str, ip_address: str):
        # dados de contexto e comportamento
        return self.send(
            endpoint="/antifraud/analyze",
            method="POST",
            payload={
                "cpf": cpf,
                "email": email,
                "ip_address": ip_address
            }
        )