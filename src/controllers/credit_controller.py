from controllers.base_controller import BaseController
from connectors.risk_connector import RiskConnector
from errors import NotFoundClient
from repositories import ClientRepository
from repositories import CreditRepository
from repositories import AccountRepository 
from datetime import datetime
from repositories.credit_invoice_repository import CreditInvoiceRepository

class CreditController(BaseController):
    """Regras de negócio para a originação e resgate de limites de crédito."""

    def __init__(self) -> None:
        super().__init__(__name__)
        self.client_repository = ClientRepository(self.context)
        self.credit_repository = CreditRepository(self.context)
        self.account_repository = AccountRepository(self.context)
        # 1. Adicionada a inicialização do repositório da fatura passando o contexto
        self.invoice_repository = CreditInvoiceRepository(self.context)

    def request_credit(self, client_key: str) -> dict:
        self.logger.debug(f"Iniciando análise de crédito para o cliente {client_key}")

        client = self.client_repository.get_by_key(client_key)
        if client is None:
            raise NotFoundClient(client_key)

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

                # 1. Cria a linha de crédito
                new_credit_line = self.credit_repository.create(credit_data)
                
                # ---> CORREÇÃO 1: Força o banco a gerar o ID da linha de crédito AGORA
                self.context.db_session.flush()

                # 2. Cria a primeira fatura zerada e aberta
                now = datetime.now()
                billing_cycle = now.strftime("%Y-%m")
                
                if now.month == 12:
                    due_date = datetime(now.year + 1, 1, 5)
                else:
                    due_date = datetime(now.year, now.month + 1, 5)

                self.invoice_repository.create_invoice(
                    credit_line_id=new_credit_line.id,
                    billing_cycle=billing_cycle,
                    due_date=due_date
                )

                # ---> CORREÇÃO 2: Salva tudo de forma definitiva no banco de dados
                self.context.db_session.commit()

                self.logger.info(f"Crédito aprovado para o cliente {client_key} e primeira fatura gerada")
                
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
        """Processa o pedido de resgate de crédito, injeta saldo na conta e regista a dívida na fatura."""
        
        amount = payload.get("amount", 0)
        if amount <= 0:
            self.logger.warning(f"Invalid withdrawal amount {amount} for client {client_key}")
            return {"status": "REJECTED", "reason": "Amount must be greater than zero"}

        self.logger.debug(f"Starting credit withdrawal of {amount} for client {client_key}")

        client = self.client_repository.get_by_key(client_key)
        if client is None:
            raise NotFoundClient(client_key)

        credit_line = self.credit_repository.get_by_client_id(client.id)
        if not credit_line or credit_line.status != "ACTIVE":
            self.logger.warning(f"No active credit line for client {client_key}")
            return {"status": "REJECTED", "reason": "No active credit line found"}

        # 1. Verifica se há uma fatura aberta antes de avançar
        open_invoice = self.invoice_repository.get_open_invoice(credit_line.id)
        if not open_invoice:
            self.logger.error(f"Nenhuma fatura aberta encontrada para a linha de crédito {credit_line.id}")
            return {"status": "ERROR", "reason": "Nenhuma fatura aberta disponível no ciclo atual"}

        fee = int(amount * float(credit_line.interest_rate))
        total_cost = amount + fee

        if credit_line.available_limit < total_cost:
            self.logger.warning(f"Insufficient limit for client {client_key}. Needs {total_cost}, has {credit_line.available_limit}")
            return {"status": "REJECTED", "reason": "Insufficient credit limit"}

    
        
    
        account = self.account_repository.get_by_client_id_for_update(client.id)
        
        if not account or account.status.enumerator != "active":
            self.logger.warning(f"No active account found for client {client_key}")
            return {"status": "REJECTED", "reason": "Client does not have an active account"}

        # 3. Desconta o limite na tabela credit_line
        self.credit_repository.deduct_limit(credit_line, total_cost)

        # 4. Adiciona a dívida (saque + juros) na fatura que está aberta
        self.invoice_repository.add_charge(open_invoice, total_cost)

        # 5. Cria a operação de depósito na conta
        operation = self.account_repository.create_operation(
            actor_client=client,
            kind_enumerator="deposit",
            amount=amount,
            fee=fee, 
            idempotency_key=idempotency_key
        )

        # 6. Executa o movimento contábil
        self.account_repository.register_transaction(
            operation=operation,
            account=account,
            type_enumerator="deposit",
            amount=amount
        )

        # 7. Efetiva todas as operações de uma só vez (A fatura será salva aqui junto com a conta e a linha de crédito)
        self.context.db_session.commit()

        self.logger.info(f"Credit withdrawal of {amount} approved for client {client_key}. Fee: {fee}")
        
        return {
            "status": "APPROVED",
            "withdrawn_amount": amount,
            "fee_charged": fee,
            "total_cost": total_cost,
            "new_account_balance": account.balance,
            "remaining_credit_limit": credit_line.available_limit,
            "invoice_amount_due": open_invoice.amount_due
        }


    def pay_invoice(self, client_key: str, payload: dict, idempotency_key: str) -> dict:
        """Processa o pagamento da fatura usando o saldo da conta e restaura o limite de crédito."""
        
        amount_to_pay = payload.get("amount", 0)
        if amount_to_pay <= 0:
            return {"status": "REJECTED", "reason": "Amount must be greater than zero"}

        self.logger.debug(f"Iniciando pagamento de fatura no valor de {amount_to_pay} para o cliente {client_key}")

        client = self.client_repository.get_by_key(client_key)
        if client is None:
            raise NotFoundClient(client_key)

    
        account = self.account_repository.get_by_client_id_for_update(client.id)
        if not account or account.status.enumerator != "active":
            return {"status": "REJECTED", "reason": "Client does not have an active account"}
            
        if account.balance < amount_to_pay:
            return {"status": "REJECTED", "reason": "Insufficient account balance to pay the invoice"}

        
        credit_line = self.credit_repository.get_by_client_id(client.id)
        open_invoice = self.invoice_repository.get_open_invoice(credit_line.id)
        
        if not open_invoice or open_invoice.amount_due == 0:
            return {"status": "REJECTED", "reason": "No outstanding balance on the open invoice"}
 
        if amount_to_pay > open_invoice.amount_due:
            amount_to_pay = open_invoice.amount_due

        
        operation = self.account_repository.create_operation(
            actor_client=client,
            kind_enumerator="withdraw",  # Assumindo que usamos 'withdraw' para saída de dinheiro
            amount=amount_to_pay,
            fee=0,
            idempotency_key=idempotency_key
        )

        self.account_repository.register_transaction(
            operation=operation,
            account=account,
            type_enumerator="withdraw",
            amount=amount_to_pay
        )

    
        open_invoice.amount_due -= amount_to_pay
        credit_line.available_limit += amount_to_pay

    
        self.context.db_session.commit()

        self.logger.info(f"Pagamento de {amount_to_pay} efetuado com sucesso para a fatura do cliente {client_key}")

        return {
            "status": "APPROVED",
            "paid_amount": amount_to_pay,
            "remaining_amount_due": open_invoice.amount_due,
            "new_account_balance": account.balance,
            "restored_credit_limit": credit_line.available_limit
        }