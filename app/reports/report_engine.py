"""Report Engine — extracts structured data for reports."""
from datetime import date
from sqlalchemy.orm import Session
from app.models.order import Order
from app.models.sale import Sale
from app.models.debt import SupplierDebt

class ReportEngine:
    def __init__(self, session: Session):
        self.session = session

    def get_orders_report(self, start_date: date, end_date: date):
        """Get all orders within a date range."""
        orders = self.session.query(Order).filter(
            Order.order_date >= start_date,
            Order.order_date <= end_date,
            Order.is_deleted == False
        ).order_by(Order.order_date.desc()).all()
        
        data = []
        for o in orders:
            cost = (o.total_material_cost or 0) + (o.labor_cost or 0) + (o.other_charges or 0)
            profit = (o.final_selling_price or 0) - cost if o.final_selling_price else 0
            
            data.append({
                "ID": o.id,
                "Reference": o.reference,
                "Date": o.order_date.strftime("%Y-%m-%d"),
                "Client": o.customer_name,
                "Statut": o.status,
                "Cout Total": cost,
                "Prix Final": o.final_selling_price or 0,
                "Benefice": profit,
                "Paiement": o.payment_status
            })
        return data

    def get_sales_report(self, start_date: date, end_date: date):
        """Get all POS sales within a date range."""
        sales = self.session.query(Sale).filter(
            Sale.sale_date >= start_date,
            Sale.sale_date <= end_date,
            Sale.is_deleted == False
        ).order_by(Sale.sale_date.desc()).all()
        
        data = []
        for s in sales:
            data.append({
                "ID": s.id,
                "Reference": s.reference,
                "Date": s.sale_date.strftime("%Y-%m-%d"),
                "Montant": s.total_amount,
                "Paiement": s.payment_method
            })
        return data

    def get_debts_report(self):
        """Get all outstanding supplier debts."""
        debts = self.session.query(SupplierDebt).filter(
            SupplierDebt.status != "payé"
        ).order_by(SupplierDebt.due_date.asc()).all()
        
        data = []
        for d in debts:
            data.append({
                "Fournisseur": d.supplier.name if d.supplier else "?",
                "Reference": d.reference,
                "Echeance": d.due_date.strftime("%Y-%m-%d") if d.due_date else "",
                "Montant Total": d.amount,
                "Paye": d.amount_paid,
                "Reste": d.amount - d.amount_paid,
                "Statut": d.status
            })
        return data
