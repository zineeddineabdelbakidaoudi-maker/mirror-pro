"""Debts (Créances) page — overview of all outstanding debts with PDF export."""
import os
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
)
from PySide6.QtCore import Qt, Signal
import win32api
import win32con

from app.ui.components.data_table import DataTable
from app.ui.components.confirm_dialog import show_error, show_success
from app.ui.theme import Theme
from app.database.engine import get_session
from app.services.customer_service import CustomerService
from app.utils.formatters import format_currency
from app.printing.debts_report import generate_debts_report

class DebtsPage(QWidget):
    open_customer_detail = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._debts_data = []
        self._total_debt = 0.0
        self._setup_ui()

    def _setup_ui(self):
        t = Theme.instance().colors
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Toolbar
        toolbar = QHBoxLayout()
        title = QLabel("Résumé global des créances")
        title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {t.text_primary};")
        toolbar.addWidget(title)
        toolbar.addStretch()

        btn_export = QPushButton("📄 Exporter PDF")
        btn_export.setProperty("class", "primary")
        btn_export.clicked.connect(self._export_pdf)
        toolbar.addWidget(btn_export)

        layout.addLayout(toolbar)

        # Summary Row
        summary_row = QHBoxLayout()
        self.count_label = QLabel("0 client(s) avec créances")
        self.count_label.setStyleSheet(f"font-size: 14px; color: {t.text_secondary};")
        summary_row.addWidget(self.count_label)
        summary_row.addStretch()

        self.total_debt_label = QLabel("Total : 0 DA")
        self.total_debt_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #ef4444;")
        summary_row.addWidget(self.total_debt_label)
        layout.addLayout(summary_row)

        # Table
        self.table = DataTable(
            ["ID Client", "Client", "Téléphone", "Nb Commandes", "Total Créance"]
        )
        self.table.row_double_clicked.connect(self._on_row_double_clicked)
        layout.addWidget(self.table)

    def refresh(self):
        session = get_session()
        try:
            svc = CustomerService(session)
            customers = svc.get_all_customers()
            
            rows = []
            debts_list = []
            total = 0.0
            
            for c in customers:
                debt_orders = svc.get_customer_debts(c.id)
                if debt_orders:
                    c_total = sum(o.remaining_balance for o in debt_orders)
                    total += c_total
                    rows.append([
                        c.id,
                        c.name,
                        c.phone or "—",
                        str(len(debt_orders)),
                        format_currency(c_total)
                    ])
                    debts_list.append({
                        "client": c.name,
                        "phone": c.phone,
                        "count": len(debt_orders),
                        "total": c_total
                    })
                    
            self.table.set_data(rows)
            self.count_label.setText(f"{len(rows)} client(s) avec créances")
            self.total_debt_label.setText(f"Total : {format_currency(total)}")
            
            self._debts_data = debts_list
            self._total_debt = total
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def filter(self, text: str):
        self.table.filter_rows(text)

    def _export_pdf(self):
        if not self._debts_data:
            show_error(self, "Export impossible", "Il n'y a aucune créance à exporter.")
            return
            
        try:
            pdf_path = generate_debts_report(self._debts_data, self._total_debt)
            # Open the PDF automatically on Windows
            win32api.ShellExecute(0, "open", pdf_path, None, ".", win32con.SW_SHOWNORMAL)
            show_success(self, "Succès", "Rapport PDF généré et ouvert.")
        except Exception as e:
            show_error(self, "Erreur d'export", f"Une erreur s'est produite: {str(e)}")

    def _on_row_double_clicked(self, client_id: int):
        self.open_customer_detail.emit(client_id)
