import os
import pytest
from datetime import date, timedelta
from app.database.engine import get_session
from app.models.product import Product
from app.models.supplier import Supplier
from app.services.pos_service import PosService
from app.services.supplier_service import SupplierService
from app.printing.printer_manager import PrinterManager

@pytest.fixture
def db_session():
    session = get_session()
    yield session
    session.rollback()
    session.close()

def test_pos_catalog_filtering(db_session):
    pos_svc = PosService(db_session)
    products = pos_svc.get_pos_products()
    for p in products:
        assert p.product_type != "raw_material"
        assert p.sellable_in_pos is True

def test_pos_stock_deduction_and_cancel(db_session):
    pos_svc = PosService(db_session)
    tracked = db_session.query(Product).filter_by(stock_tracked=True, sellable_in_pos=True).first()
    service = db_session.query(Product).filter_by(stock_tracked=False, sellable_in_pos=True).first()
    
    if tracked and service:
        initial_stock = tracked.quantity_on_hand
        
        sale = pos_svc.process_sale([
            {"product_id": tracked.id, "quantity": 1, "unit_price": tracked.selling_price},
            {"product_id": service.id, "quantity": 1, "unit_price": service.selling_price}
        ])
        
        assert tracked.quantity_on_hand == initial_stock - 1
        
        # Cancel sale
        pos_svc.cancel_sale(sale.id)
        assert tracked.quantity_on_hand == initial_stock

def test_printer_fallback_to_pdf(db_session):
    pm = PrinterManager(db_session)
    test_data = {
        "reference": "TEST-001",
        "customer": "Test",
        "date": "10/10/2026",
        "items": [{"product_name": "Miroir", "quantity": 1}],
        "final_selling_price": 5000,
        "total_payments": 5000,
        "remaining_balance": 0
    }
    company = {"name": "Test Co", "address": "123 Test", "phone": "123", "footer": "Merci"}
    
    path = pm.print_customer_receipt(test_data, company)
    assert path and path.endswith(".pdf")
    assert os.path.exists(path)

def test_supplier_debt_tracking(db_session):
    sup_svc = SupplierService(db_session)
    supplier = db_session.query(Supplier).first()
    
    if supplier:
        due_date = date.today() - timedelta(days=1)
        debt = sup_svc.add_debt(supplier.id, "INV-TEST", 10000.0, due_date)
        
        # Partial pay
        sup_svc.add_debt_payment(debt.id, 4000.0)
        assert debt.amount_paid == 4000.0
        assert debt.status == "partiellement_payé"
        
        # Overdue detection
        upcoming = sup_svc.get_upcoming_debts()
        assert any(d.id == debt.id for d in upcoming)
        
        # Full pay
        sup_svc.add_debt_payment(debt.id, 6000.0)
        assert debt.amount_paid == 10000.0
        assert debt.status == "payé"
