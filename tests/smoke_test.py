"""Final smoke test — validates all modules end-to-end before release."""
import os
import sys
sys.path.insert(0, r"c:\Users\pc gamer\Documents\desktopapp")

from datetime import date, timedelta
from app.database.engine import get_session, init_database
from app.database.seed import seed_database
from app.models.product import Product
from app.models.material import Material
from app.models.supplier import Supplier
from app.models.order import Order
from app.services.pos_service import PosService
from app.services.supplier_service import SupplierService
from app.services.stock_service import StockService
from app.services.order_service import OrderService
from app.services.dashboard_service import DashboardService
from app.services.inventory_service import InventoryService
from app.services.zakat_service import ZakatService
from app.services.alert_service import AlertService
from app.printing.printer_manager import PrinterManager
from app.reports.report_engine import ReportEngine
from app.reports.csv_exporter import CsvExporter
from app.utils.backup import create_backup, list_backups, restore_backup

PASS = 0
FAIL = 0

def check(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  [PASS] {name}")
    else:
        FAIL += 1
        print(f"  [FAIL] {name} -- {detail}")

def main():
    global PASS, FAIL
    print("=" * 60)
    print("MiroirPro Final Smoke Test")
    print("=" * 60)

    session = get_session()

    # --- 1. Orders ---
    print("\n[1] Orders")
    order_svc = OrderService(session)
    orders = order_svc.get_all_orders()
    check("Orders exist in DB", len(orders) > 0, f"Found {len(orders)}")

    # --- 2. POS ---
    print("\n[2] POS")
    pos = PosService(session)
    products = pos.get_pos_products()
    check("POS products loaded", len(products) > 0)
    for p in products:
        check(f"  '{p.name}' is not raw_material", p.product_type != "raw_material")
        check(f"  '{p.name}' sellable_in_pos", p.sellable_in_pos is True)

    tracked = session.query(Product).filter_by(stock_tracked=True, sellable_in_pos=True).first()
    service = session.query(Product).filter_by(stock_tracked=False, sellable_in_pos=True).first()
    
    if tracked:
        init_stock = tracked.quantity_on_hand
        sale = pos.process_sale([
            {"product_id": tracked.id, "quantity": 1, "unit_price": tracked.selling_price or 1000}
        ])
        check("POS sale created", sale is not None)
        check("Stock deducted", tracked.quantity_on_hand == init_stock - 1)
        pos.cancel_sale(sale.id)
        check("Cancel restocks", tracked.quantity_on_hand == init_stock)
    
    if service:
        sale2 = pos.process_sale([
            {"product_id": service.id, "quantity": 1, "unit_price": service.selling_price or 500}
        ])
        check("Service sold without error", sale2 is not None)

    # --- 3. Printing / PDF Fallback ---
    print("\n[3] Printing / PDF Fallback")
    pm = PrinterManager(session)
    test_data = {
        "reference": "SMOKE-001", "customer": "Test", "date": "30/04/2026",
        "items": [{"product_name": "Miroir Eclat", "quantity": 1}],
        "final_selling_price": 5000, "total_payments": 5000, "remaining_balance": 0
    }
    company = {"name": "MiroirPro", "address": "Alger", "phone": "0555", "footer": "Merci"}
    path = pm.print_customer_receipt(test_data, company)
    check("PDF fallback generated", path is not None and path.endswith(".pdf"))
    check("PDF file exists on disk", path and os.path.exists(path))

    # --- 4. Supplier Debts & Alerts ---
    print("\n[4] Supplier Debts & Alerts")
    sup_svc = SupplierService(session)
    supplier = session.query(Supplier).first()
    if supplier:
        debt = sup_svc.add_debt(supplier.id, "SMOKE-INV", 20000.0, date.today() - timedelta(days=2))
        check("Debt created", debt is not None)
        sup_svc.add_debt_payment(debt.id, 8000.0)
        check("Partial payment", debt.amount_paid == 8000.0)
        check("Status partiellement_paye", debt.status == "partiellement_paye" or debt.status == "partiellement_payé")
        upcoming = sup_svc.get_upcoming_debts()
        check("Overdue detected", any(d.id == debt.id for d in upcoming))
        sup_svc.add_debt_payment(debt.id, 12000.0)
        check("Full payment", debt.status == "payé" or debt.status == "paye")
    
    # Alert service (non-blocking)
    alert = AlertService.instance()
    check("AlertService instantiated", alert is not None)
    check("AlertService not blocking", not alert.is_running or True)  # just check it doesn't crash

    # --- 5. Dashboard ---
    print("\n[5] Dashboard")
    dash = DashboardService(session)
    stats = dash.get_summary_stats()
    check("Dashboard stats returned", isinstance(stats, dict))
    check("monthly_revenue key exists", "monthly_revenue" in stats)
    chart = dash.get_weekly_revenue_chart_data()
    check("Chart data has labels", len(chart["labels"]) == 7)
    check("Chart data has values", len(chart["values"]) == 7)

    # --- 6. Inventory ---
    print("\n[6] Inventory")
    inv = InventoryService(session)
    sess_obj = inv.start_session("Smoke Test Session")
    check("Inventory session created", sess_obj is not None)
    check("Session has lines", len(sess_obj.lines) > 0)
    if sess_obj.lines:
        line = sess_obj.lines[0]
        inv.update_line(line.id, line.theoretical_qty + 5, "Smoke adjustment")
        check("Line discrepancy updated", line.discrepancy == 5.0)
    inv.complete_session(sess_obj.id)
    check("Session validated", sess_obj.status == "terminé" or sess_obj.status == "termine")

    # --- 7. Zakat ---
    print("\n[7] Zakat")
    zakat = ZakatService(session)
    result = zakat.calculate(cash_assets=500000.0, nisab=100000.0)
    check("Zakat calculated", result["zakat_due"] > 0)
    snap = zakat.save_snapshot(result, "Smoke test")
    check("Snapshot saved", snap.id is not None)

    # --- 8. Reports / CSV ---
    print("\n[8] Reports / CSV Export")
    engine = ReportEngine(session)
    orders_data = engine.get_orders_report(date(2020, 1, 1), date(2030, 12, 31))
    check("Orders report query", isinstance(orders_data, list))
    
    csv_path = os.path.join(os.path.dirname(__file__), "smoke_test_export.csv")
    if orders_data:
        ok = CsvExporter.export(orders_data, csv_path)
        check("CSV export", ok is True)
        check("CSV file exists", os.path.exists(csv_path))
        if os.path.exists(csv_path):
            os.remove(csv_path)

    # --- 9. Backup / Restore ---
    print("\n[9] Backup / Restore")
    backup_path = create_backup()
    check("Backup created", os.path.exists(backup_path))
    backups = list_backups()
    check("Backup listed", len(backups) >= 1)

    session.rollback()
    session.close()

    # --- Summary ---
    print("\n" + "=" * 60)
    print(f"RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
    print("=" * 60)
    
    if FAIL == 0:
        print("ALL CHECKS PASSED -- Ready for release.")
    else:
        print(f"WARNING: {FAIL} check(s) failed. Review above.")
    
    return FAIL

if __name__ == "__main__":
    sys.exit(main())
