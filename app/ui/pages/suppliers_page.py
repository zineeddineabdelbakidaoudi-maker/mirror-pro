"""Suppliers and Debts page."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTabWidget, QDialog, QFormLayout, QLineEdit, QComboBox,
    QDoubleSpinBox, QDateEdit, QTextEdit, QFrame
)
from PySide6.QtCore import Qt, QDate
from datetime import date
from app.ui.components.data_table import DataTable
from app.ui.components.status_badge import StatusBadge
from app.ui.components.confirm_dialog import show_error, show_success
from app.database.engine import get_session
from app.services.supplier_service import SupplierService
from app.utils.formatters import format_currency, format_date

class SuppliersPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.tab_suppliers = QWidget()
        self.tab_debts = QWidget()
        
        self.tabs.addTab(self.tab_suppliers, "Fournisseurs")
        self.tabs.addTab(self.tab_debts, "Dettes & Paiements")
        layout.addWidget(self.tabs)

        self._setup_suppliers_tab()
        self._setup_debts_tab()

    def _setup_suppliers_tab(self):
        layout = QVBoxLayout(self.tab_suppliers)
        layout.setContentsMargins(24, 24, 24, 24)
        
        toolbar = QHBoxLayout()
        btn_add = QPushButton("+ Nouveau fournisseur")
        btn_add.setProperty("class", "primary")
        btn_add.clicked.connect(self._add_supplier)
        toolbar.addWidget(btn_add)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        cols = ["ID", "Nom", "Téléphone", "Délai Paimt. (Jours)", "Notes"]
        self.suppliers_table = DataTable(cols)
        self.suppliers_table.row_double_clicked.connect(self._edit_supplier)
        layout.addWidget(self.suppliers_table)

    def _setup_debts_tab(self):
        layout = QVBoxLayout(self.tab_debts)
        layout.setContentsMargins(24, 24, 24, 24)
        
        toolbar = QHBoxLayout()
        btn_add = QPushButton("+ Nouvelle dette (Facture)")
        btn_add.setProperty("class", "primary")
        btn_add.clicked.connect(self._add_debt)
        toolbar.addWidget(btn_add)
        
        btn_pay = QPushButton("Enregistrer paiement")
        btn_pay.clicked.connect(self._add_debt_payment)
        toolbar.addWidget(btn_pay)
        
        toolbar.addStretch()
        self.debts_total_label = QLabel()
        self.debts_total_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        toolbar.addWidget(self.debts_total_label)
        layout.addLayout(toolbar)

        cols = ["ID", "Fournisseur", "Réf", "Montant Total", "Payé", "Reste", "Date Limite", "Statut"]
        self.debts_table = DataTable(cols)
        layout.addWidget(self.debts_table)

    def refresh(self):
        session = get_session()
        try:
            svc = SupplierService(session)
            
            # Suppliers
            suppliers = svc.get_all_suppliers()
            s_rows = []
            for s in suppliers:
                s_rows.append([s.id, s.name, s.phone or "", s.default_payment_days, s.notes or ""])
            self.suppliers_table.set_data(s_rows)
            
            # Debts
            debts = svc.get_debts()
            d_rows = []
            total_unpaid = 0.0
            
            for d in debts:
                rem = d.amount - d.amount_paid
                if d.status != "payé":
                    total_unpaid += rem
                    
                sup_name = d.supplier.name if d.supplier else "?"
                d_rows.append([
                    d.id, sup_name, d.reference,
                    format_currency(d.amount),
                    format_currency(d.amount_paid),
                    format_currency(rem),
                    format_date(d.due_date),
                    d.status
                ])
            self.debts_table.set_data(d_rows)
            self.debts_total_label.setText(f"Reste total à payer: {format_currency(total_unpaid)}")
            
        finally:
            session.close()

    def filter(self, text: str):
        self.suppliers_table.filter_rows(text)
        self.debts_table.filter_rows(text)

    def _add_supplier(self):
        dlg = SupplierDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = get_session()
            try:
                svc = SupplierService(session)
                svc.create_supplier(**data)
                show_success(self, "Succès", "Fournisseur ajouté")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _edit_supplier(self, s_id: int):
        dlg = SupplierDialog(self, s_id)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = get_session()
            try:
                svc = SupplierService(session)
                svc.update_supplier(s_id, **data)
                show_success(self, "Succès", "Fournisseur modifié")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _add_debt(self):
        dlg = DebtDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = get_session()
            try:
                svc = SupplierService(session)
                svc.add_debt(**data)
                show_success(self, "Succès", "Dette enregistrée")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _add_debt_payment(self):
        d_id = self.debts_table.get_selected_id()
        if not d_id:
            show_error(self, "Sélection", "Veuillez sélectionner une dette")
            return
            
        dlg = DebtPaymentDialog(self, d_id)
        if dlg.exec() == QDialog.Accepted:
            amount, method, notes = dlg.get_data()
            session = get_session()
            try:
                svc = SupplierService(session)
                svc.add_debt_payment(d_id, amount, method, notes)
                show_success(self, "Succès", "Paiement enregistré")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()


class SupplierDialog(QDialog):
    def __init__(self, parent=None, supplier_id: int = None):
        super().__init__(parent)
        self.supplier_id = supplier_id
        self.setWindowTitle("Fournisseur")
        self.setMinimumWidth(400)
        self._setup_ui()
        if supplier_id: self._load()

    def _setup_ui(self):
        layout = QFormLayout(self)
        self.name_input = QLineEdit()
        layout.addRow("Nom *:", self.name_input)
        self.phone_input = QLineEdit()
        layout.addRow("Téléphone:", self.phone_input)
        self.address_input = QLineEdit()
        layout.addRow("Adresse:", self.address_input)
        self.days_spin = QDoubleSpinBox()
        self.days_spin.setRange(0, 365)
        self.days_spin.setDecimals(0)
        self.days_spin.setValue(30)
        layout.addRow("Délai (jours):", self.days_spin)
        self.notes_input = QTextEdit()
        layout.addRow("Notes:", self.notes_input)
        
        btns = QHBoxLayout()
        bc = QPushButton("Annuler"); bc.clicked.connect(self.reject); btns.addWidget(bc)
        bs = QPushButton("Enregistrer"); bs.setProperty("class", "primary"); bs.clicked.connect(self.accept); btns.addWidget(bs)
        layout.addRow(btns)

    def _load(self):
        session = get_session()
        try:
            svc = SupplierService(session)
            s = svc.get_supplier(self.supplier_id)
            if s:
                self.name_input.setText(s.name)
                self.phone_input.setText(s.phone or "")
                self.address_input.setText(s.address or "")
                self.days_spin.setValue(s.default_payment_days)
                self.notes_input.setText(s.notes or "")
        finally:
            session.close()

    def get_data(self):
        return {
            "name": self.name_input.text().strip(),
            "phone": self.phone_input.text().strip() or None,
            "address": self.address_input.text().strip() or None,
            "default_payment_days": int(self.days_spin.value()),
            "notes": self.notes_input.toPlainText().strip() or None,
        }


class DebtDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouvelle Dette")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        self.sup_combo = QComboBox()
        
        session = get_session()
        try:
            svc = SupplierService(session)
            sups = svc.get_all_suppliers()
            for s in sups:
                self.sup_combo.addItem(s.name, s.id)
        finally:
            session.close()
            
        layout.addRow("Fournisseur *:", self.sup_combo)
        self.ref_input = QLineEdit()
        layout.addRow("Réf (Facture):", self.ref_input)
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 99999999)
        self.amount_spin.setSuffix(" DA")
        layout.addRow("Montant Total:", self.amount_spin)
        self.due_date = QDateEdit(QDate.currentDate().addDays(30))
        self.due_date.setCalendarPopup(True)
        layout.addRow("Date Limite:", self.due_date)
        self.desc_input = QLineEdit()
        layout.addRow("Description:", self.desc_input)
        
        btns = QHBoxLayout()
        bc = QPushButton("Annuler"); bc.clicked.connect(self.reject); btns.addWidget(bc)
        bs = QPushButton("Enregistrer"); bs.setProperty("class", "primary"); bs.clicked.connect(self.accept); btns.addWidget(bs)
        layout.addRow(btns)

    def get_data(self):
        qd = self.due_date.date()
        return {
            "supplier_id": self.sup_combo.currentData(),
            "reference": self.ref_input.text().strip() or "SANS_REF",
            "amount": self.amount_spin.value(),
            "due_date": date(qd.year(), qd.month(), qd.day()),
            "description": self.desc_input.text().strip() or None,
        }


class DebtPaymentDialog(QDialog):
    def __init__(self, parent, debt_id: int):
        super().__init__(parent)
        self.setWindowTitle("Paiement Dette")
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0, 99999999)
        self.amount_spin.setSuffix(" DA")
        layout.addRow("Montant:", self.amount_spin)
        self.method_combo = QComboBox()
        self.method_combo.addItems(["virement", "chèque", "espèces"])
        layout.addRow("Mode:", self.method_combo)
        self.notes_input = QLineEdit()
        layout.addRow("Notes:", self.notes_input)
        
        btns = QHBoxLayout()
        bc = QPushButton("Annuler"); bc.clicked.connect(self.reject); btns.addWidget(bc)
        bs = QPushButton("Enregistrer"); bs.setProperty("class", "primary"); bs.clicked.connect(self.accept); btns.addWidget(bs)
        layout.addRow(btns)

    def get_data(self):
        return self.amount_spin.value(), self.method_combo.currentText(), self.notes_input.text().strip() or None
