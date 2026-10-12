import os
from connectors.rest_connector import RestConnector

class RiskConnector(RestConnector):
    def __init__(self):
        super().__init__(
            class_name=self.__class__.__name__,
            base_url=os.getenv("RISK_API_URL", "http://mock-server:8080"),
            timeout=int(os.getenv("API_TIMEOUT", "5")),
            internal_token=os.getenv("INTERNAL_TOKEN", "mock-token")
        )

    def get_risk_profile(self, document_number: str):
        return self.send(
            endpoint=f"/api/risk/score/{document_number}",
            method="GET"
        )