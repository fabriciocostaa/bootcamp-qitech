from sqlalchemy import BIGINT, CHAR, Column, DateTime, ForeignKey, Integer, String, VARCHAR
from sqlalchemy.orm import relationship
from models.base import Base

class InvoiceStatus(Base):
    __tablename__ = "invoice_status"
    
    id = Column(Integer, primary_key=True)
    enumerator = Column(VARCHAR(50), nullable=False, unique=True)
    created_at = Column(DateTime, nullable=False)

class CreditInvoice(Base):
    __tablename__ = "credit_invoice"
    
    id = Column(Integer, primary_key=True)
    invoice_key = Column(CHAR(36), nullable=False, unique=True)
    credit_line_id = Column(Integer, ForeignKey("credit_line.id"), nullable=False)
    status_id = Column(Integer, ForeignKey(InvoiceStatus.id), nullable=False)
    
    billing_cycle = Column(VARCHAR(7), nullable=False)
    amount_due = Column(BIGINT, nullable=False, default=0)
    due_date = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    
    
    status = relationship("InvoiceStatus", foreign_keys=[status_id], lazy="selectin")
    credit_line = relationship("CreditLine", lazy="selectin")
    status_events = relationship(
        "InvoiceStatusEvent", 
        back_populates="invoice",
        order_by="asc(InvoiceStatusEvent.event_datetime)"
    )

class InvoiceStatusEvent(Base):
    __tablename__ = "invoice_status_event"
    
    id = Column(Integer, primary_key=True)
    invoice_id = Column(Integer, ForeignKey("credit_invoice.id"), nullable=False)
    status_id = Column(Integer, ForeignKey(InvoiceStatus.id), nullable=False)
    event_datetime = Column(DateTime, nullable=False)
    created_at = Column(DateTime, nullable=False)
    
   
    invoice = relationship("CreditInvoice", back_populates="status_events")
    status = relationship("InvoiceStatus", foreign_keys=[status_id], lazy="selectin")