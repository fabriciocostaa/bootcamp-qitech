import uuid
from datetime import datetime

from database import Context
from models.credit_invoice import CreditInvoice, InvoiceStatus, InvoiceStatusEvent

class CreditInvoiceRepository:
    
    def __init__(self, context: Context) -> None:
        self.session = context.db_session

    def get_status(self, enumerator: str) -> InvoiceStatus:
        return self.session.query(InvoiceStatus).filter_by(enumerator=enumerator).first()

    def create_invoice(self, credit_line_id: int, billing_cycle: str, due_date: datetime) -> CreditInvoice:
        status_open = self.get_status("open")
        
        new_invoice = CreditInvoice(
            invoice_key=str(uuid.uuid4()),
            credit_line_id=credit_line_id,
            status_id=status_open.id,
            billing_cycle=billing_cycle,
            amount_due=0,
            due_date=due_date,
            created_at=datetime.now()
        )
        self.session.add(new_invoice)
        self.session.flush()

        status_event = InvoiceStatusEvent(
            invoice_id=new_invoice.id,
            status_id=status_open.id,
            event_datetime=datetime.now(),
            created_at=datetime.now()
        )
        self.session.add(status_event)
        self.session.flush()

        return new_invoice

    def get_open_invoice(self, credit_line_id: int) -> CreditInvoice:
        status_open = self.get_status("open")
        return self.session.query(CreditInvoice).filter_by(
            credit_line_id=credit_line_id,
            status_id=status_open.id
        ).with_for_update().populate_existing().first()

    def add_charge(self, invoice: CreditInvoice, amount_to_add: int) -> CreditInvoice:
        invoice.amount_due += amount_to_add
        self.session.add(invoice)
        self.session.flush()
        
        return invoice