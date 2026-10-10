from typing import List
from models import CreditLine

class creditDTO:

    @staticmethod
    def obj_to_dict(credit_line: CreditLine) -> dict:
        """A entidade completa da linha de crédito."""
        dto = dict()
        dto["credit_line_key"] = credit_line.credit_line_key
        dto["client_id"] = credit_line.client_id
        dto["approved_limit"] = credit_line.approved_limit
        dto["available_limit"] = credit_line.available_limit
        dto["interest_rate"] = float(credit_line.interest_rate) if credit_line.interest_rate else 0.02
        dto["status"] = credit_line.status

        if hasattr(credit_line, "created_at") and credit_line.created_at:
            dto["created_at"] = credit_line.created_at.isoformat()

        return dto

    @staticmethod
    def only_obj_key(credit_line: CreditLine) -> dict:
        """Devolve apenas a chave, mantendo o padrão usado no cadastro de clientes."""
        dto = dict()
        dto["credit_line_key"] = credit_line.credit_line_key
        return dto

    @staticmethod
    def list_obj_to_list_dict(credit_list: List[CreditLine]) -> List[dict]:
        credit_dict_list = []
        for credit in credit_list:
            credit_dict_list.append(creditDTO.obj_to_dict(credit))
        return credit_dict_list

    @staticmethod
    def approval_response(limit_cents: int, credit_line_key: str) -> dict:
        return {
            "status": "APPROVED",
            "limit_cents": limit_cents,
            "credit_line_key": credit_line_key
        }

    @staticmethod
    def rejection_response(reason: str, status: str = "REJECTED") -> dict:
        return {
            "status": status,
            "reason": reason
        }

    @staticmethod
    def withdraw_response(withdrawn_amount: int, fee: float, remaining_limit: int, invoice_due: float, account_balance: int) -> dict:
        return {
            "status": "APPROVED",
            "withdrawn_amount": withdrawn_amount,
            "fee_charged": fee,
            "total_cost": withdrawn_amount + fee,
            "remaining_credit_limit": remaining_limit,
            "invoice_due_amount": invoice_due,
            "invoice_amount_due": invoice_due,
            "new_account_balance": account_balance
        }

    @staticmethod
    def payment_response(paid_amount: int, remaining_due: float, account_balance: int, restored_limit: int) -> dict:
        return {
            "status": "APPROVED",
            "paid_amount": paid_amount,
            "remaining_amount_due": remaining_due,
            "new_account_balance": account_balance,
            "restored_credit_limit": restored_limit
        }