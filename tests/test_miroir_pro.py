"""Test suite for MiroirPro — order costing, stock reservation, debt reminders, payments."""
import os
import pytest
from datetime import date, timedelta
from app.database.engine import get_session
from app.models.product import Product
from app.models.material import Material
from app.models.supplier import Supplier
from app.models.order import Order
from app.models.sale import Sale
from app.models.debt import SupplierDebt
from app.services.pos_service import PosService
from app.services.supplier_service import SupplierService
from app.services.stock_service import StockService
from app.services.order_service import OrderService
from app.services.zakat_service import ZakatService
from app.services.inventory_service import InventoryService
from app.printing.printer_manager import PrinterManager
from app.reports.csv_exporter import CsvExporter
from app.reports.report_engine import ReportEngine
from app.utils.backup import create_backup, list_backups


@pytest.fixture
def db_session():
    session = get_session()
    yield session
    session.rollback()
    session.close()


# ============================================================
# POS Tests
# ============================================================

class TestPOS:
    def test_catalog_excludes_raw_materials(self, db_session):
        pos = PosService(db_session)
        products = pos.get_pos_products()
        for p in products:
            assert p.product_type != "raw_material", f"Raw material in POS: {p.name}"
            assert p.sellable_in_pos is True

    def test_stock_deduction_tracked_product(self, db_session):
        pos = PosService(db_session)
        tracked = db_session.query(Product).filter_by(
            stock_tracked=True, sellable_in_pos=True
        ).first()
        if not tracked:
            pytest.skip("No tracked product in DB")

        initial = tracked.quantity_on_hand
        sale = pos.process_sale([
            {"product_id": tracked.id, "quantity": 1, "unit_price": tracked.selling_price}
        ])
        assert tracked.quantity_on_hand == initial - 1

    def test_service_no_stock_deduction(self, db_session):
        pos = PosService(db_session)
        service = db_session.query(Product).filter_by(
            stock_tracked=False, sellable_in_pos=True
        ).first()
        if not service:
            pytest.skip("No service product in DB")

        sale = pos.process_sale([
            {"product_id": service.id, "quantity": 2, "unit_price": service.selling_price}
        ])
        assert sale is not None  # No crash, no stock error

    def test_cancel_sale_restocks(self, db_session):
        pos = PosService(db_session)
        tracked = db_session.query(Product).filter_by(
            stock_tracked=True, sellable_in_pos=True
        ).first()
        if not tracked:
            pytest.skip("No tracked product in DB")

        initial = tracked.quantity_on_hand
        sale = pos.process_sale([
            {"product_id": tracked.id, "quantity": 1, "unit_price": tracked.selling_price}
        ])
        assert tracked.quantity_on_hand == initial - 1
        pos.cancel_sale(sale.id)
        assert tracked.quantity_on_hand == initial

    def test_cancel_already_cancelled_raises(self, db_session):
        pos = PosService(db_session)
        service = db_session.query(Product).filter_by(
            stock_tracked=False, sellable_in_pos=True
        ).first()
        if not service:
            pytest.skip("No service product in DB")
        sale = pos.process_sale([
            {"product_id": service.id, "quantity": 1, "unit_price": service.selling_price}
        ])
        pos.cancel_sale(sale.id)
        with pytest.raises(ValueError, match="annulée"):
            pos.cancel_sale(sale.id)


# ============================================================
# Printing Tests
# ============================================================

class TestPrinting:
    def test_pdf_fallback_always_works(self, db_session):
        pm = PrinterManager(db_session)
        test_data = {
            "reference": "TEST-PRINT",
            "customer": "Client Test",
            "date": "01/01/2026",
            "items": [{"product_name": "Miroir Eclat", "quantity": 1}],
            "final_selling_price": 5000,
            "total_payments": 5000,
            "remaining_balance": 0,
        }
        company = {"name": "Test Co", "address": "Alger", "phone": "0555", "footer": "Merci"}
        path = pm.print_customer_receipt(test_data, company)
        assert path is not None
        assert path.endswith(".pdf")
        assert os.path.exists(path)


# ============================================================
# Supplier Debt Tests
# ============================================================

class TestSupplierDebts:
    def test_partial_payment_updates_balance(self, db_session):
        svc = SupplierService(db_session)
        supplier = db_session.query(Supplier).first()
        if not supplier:
            pytest.skip("No supplier in DB")

        debt = svc.add_debt(supplier.id, "INV-T1", 10000.0, date.today())
        svc.add_debt_payment(debt.id, 4000.0)
        assert debt.amount_paid == 4000.0
        assert debt.status == "partiellement_payé"

    def test_full_payment_marks_paid(self, db_session):
        svc = SupplierService(db_session)
        supplier = db_session.query(Supplier).first()
        if not supplier:
            pytest.skip("No supplier in DB")

        debt = svc.add_debt(supplier.id, "INV-T2", 5000.0, date.today())
        svc.add_debt_payment(debt.id, 5000.0)
        assert debt.amount_paid == 5000.0
        assert debt.status == "payé"

    def test_overdue_debt_detected(self, db_session):
        svc = SupplierService(db_session)
        supplier = db_session.query(Supplier).first()
        if not supplier:
            pytest.skip("No supplier in DB")

        yesterday = date.today() - timedelta(days=1)
        debt = svc.add_debt(supplier.id, "INV-T3", 8000.0, yesterday)
        upcoming = svc.get_upcoming_debts()
        assert any(d.id == debt.id for d in upcoming)


# ============================================================
# Stock / Reservation Tests
# ============================================================

class TestStock:
    def test_stock_in_increases(self, db_session):
        stock_svc = StockService(db_session)
        mat = db_session.query(Material).filter_by(is_deleted=False).first()
        if not mat:
            pytest.skip("No material in DB")

        initial = mat.quantity_on_hand
        stock_svc.stock_in(mat.id, 10.0, reason="Test restock")
        assert mat.quantity_on_hand == initial + 10.0

    def test_stock_out_insufficient_raises(self, db_session):
        stock_svc = StockService(db_session)
        mat = db_session.query(Material).filter_by(is_deleted=False).first()
        if not mat:
            pytest.skip("No material in DB")

        with pytest.raises(ValueError, match="Stock insuffisant"):
            stock_svc.stock_out(mat.id, mat.quantity_on_hand + mat.quantity_reserved + 99999)


# ============================================================
# Zakat Tests
# ============================================================

class TestZakat:
    def test_zakat_calculation_below_nisab(self, db_session):
        svc = ZakatService(db_session)
        result = svc.calculate(cash_assets=0.0, nisab=999_999_999)
        assert result["zakat_due"] == 0.0

    def test_zakat_calculation_above_nisab(self, db_session):
        svc = ZakatService(db_session)
        result = svc.calculate(cash_assets=10_000_000.0, nisab=100_000.0)
        assert result["zakat_due"] > 0


# ============================================================
# Reports / CSV Tests
# ============================================================

class TestReports:
    def test_csv_export_creates_file(self, db_session, tmp_path):
        data = [{"Col1": "val1", "Col2": "val2"}, {"Col1": "val3", "Col2": "val4"}]
        path = str(tmp_path / "test_export.csv")
        ok = CsvExporter.export(data, path)
        assert ok is True
        assert os.path.exists(path)

    def test_report_engine_orders(self, db_session):
        engine = ReportEngine(db_session)
        data = engine.get_orders_report(date(2020, 1, 1), date(2030, 12, 31))
        assert isinstance(data, list)


# ============================================================
# Backup Tests
# ============================================================

class TestBackup:
    def test_create_and_list_backup(self):
        path = create_backup()
        assert os.path.exists(path)
        backups = list_backups()
        assert len(backups) >= 1
        assert backups[0]["filename"].endswith(".db")
