from controllers.base_controller import BaseController
from connectors.risk_connector import RiskConnector
from dtos.credit_dto import creditDTO
from errors import NotFoundSampleEntity
from repositories import ClientRepository
from repositories import CreditRepository
from repositories import AccountRepository 

class CreditController(BaseController):
    """Regras de negócio para a originação e resgate de limites de crédito."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context)
        self.credit_repository = CreditRepository(self.context)
        self.account_repository = AccountRepository(self.context)

    def request_credit(self, client_key: str) -> dict:
        self.logger.debug(f"Iniciando análise de crédito para o cliente {client_key}")

        client = self.client_repository.get_by_key(client_key)
        if client is None:
            raise NotFoundSampleEntity(client_key)

        risk_connector = RiskConnector()
        risk_response = risk_connector.get_risk_profile(client.document_number)

        if risk_response.status == 200:
            risk_data = risk_response.json
            
            score = risk_data.get("score", 0)
            approved_limit_cents = risk_data.get("recommended_limit_cents", 0)

            if score >= 600 and approved_limit_cents > 0:
                credit_data = {
                    "client_id": client.id,
                    "approved_limit": approved_limit_cents,
                    "available_limit": approved_limit_cents,
                    "interest_rate": 0.02  # juros fixos de 2% ao mês
                }

                new_credit_line = self.credit_repository.create(credit_data)

                self.logger.info(f"Crédito aprovado para o cliente {client_key}")
                
                return {
                    "status": "APPROVED", 
                    "limit_cents": approved_limit_cents,
                    "credit_line_key": new_credit_line.credit_line_key
                }
            
            else:
                self.logger.info(f"Crédito recusado para o cliente {client_key} (Score: {score})")
                return {"status": "REJECTED", "reason": "Score insuficiente"}
        else:
            self.logger.error(f"Falha ao consultar bureau de crédito para o cliente {client_key}")
            return {"status": "ERROR", "reason": "Serviço indisponível"}

    def withdraw_credit(self, client_key: str, payload: dict, idempotency_key: str) -> dict:
        """Processa o pedido de resgate de crédito e injeta saldo na conta."""
        
        amount = payload.get("amount", 0)
        if amount <= 0:
            self.logger.warning(f"Invalid withdrawal amount {amount} for client {client_key}")
            return {"status": "REJECTED", "reason": "Amount must be greater than zero"}

        self.logger.debug(f"Starting credit withdrawal of {amount} for client {client_key}")

        client = self.client_repository.get_by_key(client_key)
        if client is None:
            raise NotFoundSampleEntity(client_key)

        credit_line = self.credit_repository.get_by_client_id(client.id)
        if not credit_line or credit_line.status != "ACTIVE":
            self.logger.warning(f"No active credit line for client {client_key}")
            return {"status": "REJECTED", "reason": "No active credit line found"}

        fee = int(amount * float(credit_line.interest_rate))
        total_cost = amount + fee

        if credit_line.available_limit < total_cost:
            self.logger.warning(f"Insufficient limit for client {client_key}. Needs {total_cost}, has {credit_line.available_limit}")
            return {"status": "REJECTED", "reason": "Insufficient credit limit"}

        # --- ORQUESTRAÇÃO DA TRANSAÇÃO NO BANCO DE DADOS ---
        
        # 1. Bloqueia a conta do cliente para atualização segura
        account = self.account_repository.get_by_client_id_for_update(client.id)
        
        if not account or account.status.enumerator != "active":
            self.logger.warning(f"No active account found for client {client_key}")
            return {"status": "REJECTED", "reason": "Client does not have an active account"}

        # 2. Desconta o limite na tabela credit_line
        self.credit_repository.deduct_limit(credit_line, total_cost)

        # 3. Cria a operação de depósito na conta
        operation = self.account_repository.create_operation(
            actor_client=client,
            kind_enumerator="deposit",
            amount=amount,
            fee=fee, 
            idempotency_key=idempotency_key
        )

        # 4. Executa o movimento contábil
        self.account_repository.register_transaction(
            operation=operation,
            account=account,
            type_enumerator="deposit",
            amount=amount
        )

        # 5. Efetiva todas as operações de uma só vez
        self.context.db_session.commit()

        self.logger.info(f"Credit withdrawal of {amount} approved for client {client_key}. Fee: {fee}")
        
        return {
            "status": "APPROVED",
            "withdrawn_amount": amount,
            "fee_charged": fee,
            "total_cost": total_cost,
            "new_account_balance": account.balance,
            "remaining_credit_limit": credit_line.available_limit
        }