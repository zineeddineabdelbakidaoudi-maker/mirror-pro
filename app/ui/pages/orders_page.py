"""Orders list page — view and manage all orders."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog,
    QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QLabel,
    QDateEdit, QTextEdit, QFrame, QCompleter, QSizePolicy, QScrollArea
)
from PySide6.QtCore import Qt, Signal, QDate, QStringListModel
from datetime import date
from app.ui.components.data_table import DataTable
from app.ui.components.status_badge import StatusBadge, STATUS_DISPLAY
from app.ui.components.confirm_dialog import show_error, show_success
from app.database.engine import get_session
from app.services.order_service import OrderService
from app.utils.formatters import format_currency, format_date
from app.utils.constants import OrderStatus, OrderUrgency


class OrdersPage(QWidget):
    open_order_detail = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Toolbar
        toolbar = QHBoxLayout()
        btn_new = QPushButton("+ Nouvelle commande")
        btn_new.setProperty("class", "primary")
        btn_new.setCursor(Qt.PointingHandCursor)
        btn_new.clicked.connect(self._show_new_order)
        toolbar.addWidget(btn_new)

        # Filter combo
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Toutes", "all")
        self.filter_combo.addItem("Brouillon", "brouillon")
        self.filter_combo.addItem("En attente", "pending")
        self.filter_combo.addItem("En production", "production")
        self.filter_combo.addItem("Livrées", "livrée")
        self.filter_combo.addItem("Annulées", "annulée")
        self.filter_combo.currentIndexChanged.connect(lambda: self.refresh())
        toolbar.addWidget(QLabel("Filtre:"))
        toolbar.addWidget(self.filter_combo)

        toolbar.addStretch()

        self.count_label = QLabel()
        self.count_label.setStyleSheet("font-size: 13px;")
        toolbar.addWidget(self.count_label)

        layout.addLayout(toolbar)

        # Table
        columns = [
            "ID", "Référence", "Client", "Date", "Livraison prévue",
            "Urgence", "Statut", "Paiement", "Coût estimé", "Prix final",
        ]
        self.table = DataTable(columns)
        self.table.row_double_clicked.connect(self._on_open_order)
        layout.addWidget(self.table)

    def refresh(self):
        session = get_session()
        try:
            svc = OrderService(session)
            filter_val = self.filter_combo.currentData()

            if filter_val == "pending":
                orders = svc.get_pending_orders()
            elif filter_val == "production":
                orders = [o for o in svc.get_all_orders()
                          if o.status in ("en_production", "en_découpe", "en_assemblage", "finition")]
            elif filter_val and filter_val != "all":
                orders = [o for o in svc.get_all_orders() if o.status == filter_val]
            else:
                orders = svc.get_all_orders()

            rows = []
            for o in orders:
                rows.append([
                    o.id,
                    o.reference,
                    o.customer_name,
                    format_date(o.order_date),
                    format_date(o.expected_delivery_date),
                    STATUS_DISPLAY.get(o.urgency, o.urgency),
                    STATUS_DISPLAY.get(o.status, o.status),
                    STATUS_DISPLAY.get(o.payment_status, o.payment_status),
                    format_currency(o.estimated_cost),
                    format_currency(o.final_selling_price),
                ])
            self.table.set_data(rows)
            self.count_label.setText(f"{len(rows)} commande(s)")
        finally:
            session.close()

    def filter(self, text: str):
        self.table.filter_rows(text)

    def _on_open_order(self, order_id: int):
        self.open_order_detail.emit(order_id)

    def _show_new_order(self):
        dlg = NewOrderDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = get_session()
            try:
                svc = OrderService(session)
                order = svc.create_order(**data)
                show_success(self, "Succès", f"Commande {order.reference} créée")
                self.refresh()
                self.open_order_detail.emit(order.id)
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()


class NewOrderDialog(QDialog):
    """Dialog for creating a new customer order with client autocomplete and dual-unit materials."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouvelle commande")
        self.setMinimumWidth(800)
        self.setMinimumHeight(700)
        self.resize(900, 800)
        self.materials = []
        self._item_rows = []  # Keep track of active item row widgets
        self.customers = []
        self._load_data()
        self._setup_ui()

    def _load_data(self):
        session = get_session()
        try:
            from app.services.stock_service import StockService
            from app.services.customer_service import CustomerService
            svc = StockService(session)
            self.materials = svc.get_all_materials()
            cust_svc = CustomerService(session)
            self.customers = cust_svc.get_all_customers()
        except Exception:
            # CustomerService may not exist yet — graceful fallback
            from app.services.stock_service import StockService
            svc = StockService(session)
            self.materials = svc.get_all_materials()
        finally:
            session.close()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Nouvelle commande client")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addRow(title)

        # ── Client autocomplete ──────────────────────────────
        client_lbl = QLabel("Client *:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom du client (existant ou nouveau)")
        customer_names = [c.name for c in self.customers]
        completer = QCompleter(customer_names)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.name_input.setCompleter(completer)
        self.name_input.textChanged.connect(self._on_client_name_changed)
        layout.addRow(client_lbl, self.name_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("0555 XXX XXX")
        layout.addRow("Téléphone:", self.phone_input)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Adresse (optionnel)")
        layout.addRow("Adresse:", self.address_input)

        self.delivery_date = QDateEdit()
        self.delivery_date.setDate(QDate.currentDate().addDays(7))
        self.delivery_date.setCalendarPopup(True)
        self.delivery_date.setDisplayFormat("dd/MM/yyyy")
        layout.addRow("Date livraison:", self.delivery_date)

        self.urgency_combo = QComboBox()
        for u in OrderUrgency:
            self.urgency_combo.addItem(u.label, u.value)
        layout.addRow("Urgence:", self.urgency_combo)

        # ── Items section ────────────────────────────────────
        items_title = QLabel("Matières (Optionnel)")
        items_title.setStyleSheet("font-size: 14px; font-weight: bold; margin-top: 10px;")
        layout.addRow(items_title)

        unit_hint = QLabel("💡 Sélectionnez la matière puis l'unité (principale ou secondaire si dispo)")
        unit_hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addRow(unit_hint)

        self.items_container = QVBoxLayout()
        self.items_container.setSpacing(8)
        self.items_container.addStretch()
        
        container_widget = QWidget()
        container_widget.setLayout(self.items_container)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setMinimumHeight(250)
        scroll.setWidget(container_widget)
        scroll.setStyleSheet("QScrollArea { border: 1px solid #ccc; border-radius: 6px; }")
        
        layout.addRow(scroll)

        btn_add_item = QPushButton("+ Ajouter matière")
        btn_add_item.clicked.connect(self._add_item_row)
        layout.addRow("", btn_add_item)

        self.est_price_label = QLabel("Total estimé (prix vente): 0 DA")
        self.est_price_label.setStyleSheet("font-weight: bold; color: #EAB308; font-size: 14px;")
        layout.addRow("", self.est_price_label)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(60)
        self.notes_input.setPlaceholderText("Notes (optionnel)")
        layout.addRow("Notes:", self.notes_input)

        self.deposit_spin = QDoubleSpinBox()
        self.deposit_spin.setRange(0, 99999999)
        self.deposit_spin.setSuffix(" DA")
        layout.addRow("Versement initial:", self.deposit_spin)

        self.deposit_method = QComboBox()
        self.deposit_method.addItems(["espèces", "chèque", "virement"])
        layout.addRow("Mode paiement:", self.deposit_method)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_save = QPushButton("Créer la commande")
        btn_save.setProperty("class", "primary")
        btn_save.clicked.connect(self._validate)
        btn_layout.addWidget(btn_save)
        layout.addRow(btn_layout)

    def _on_client_name_changed(self, text: str):
        """Auto-fill phone/address if existing client selected."""
        existing = next((c for c in self.customers if c.name.lower() == text.lower()), None)
        if existing:
            self.phone_input.setText(existing.phone or "")
            self.address_input.setText(existing.address or "")

    def _add_item_row(self):
        row_widget = QFrame()
        row_widget.setStyleSheet("QFrame { border: 1px solid #333; border-radius: 6px; padding: 4px; }")
        row_layout = QVBoxLayout(row_widget)
        row_layout.setContentsMargins(6, 6, 6, 6)
        row_layout.setSpacing(6)

        top_row = QHBoxLayout()

        # Material combo
        mat_combo = QComboBox()
        mat_combo.addItem("-- Sélectionner matière --", None)
        for m in self.materials:
            avail = f"{m.quantity_available:.1f} {m.unit}"
            mat_combo.addItem(f"{m.designation} ({avail})", m.id)
        mat_combo.setMinimumWidth(220)
        
        # Remaining stock label
        stock_lbl = QLabel("")
        stock_lbl.setStyleSheet("color: #0284c7; font-size: 11px; font-weight: bold;")
        top_row.addWidget(mat_combo, 4)
        top_row.addWidget(stock_lbl, 2)

        # Unit combo (populated when material selected)
        unit_combo = QComboBox()
        unit_combo.addItem("-- unité --", "primary")
        unit_combo.setFixedWidth(130)

        top_row.addWidget(mat_combo, 4)
        top_row.addWidget(unit_combo, 2)

        bottom_row = QHBoxLayout()
        qty_spin = QDoubleSpinBox()
        qty_spin.setRange(0.01, 9999)
        qty_spin.setValue(1)
        qty_spin.setDecimals(2)
        qty_spin.setFixedWidth(90)

        price_label = QLabel("0 DA/u")
        price_label.setStyleSheet("font-weight: 500; color: #EAB308; min-width: 80px;")

        line_total_label = QLabel("= 0 DA")
        line_total_label.setStyleSheet("font-weight: bold; min-width: 90px;")

        btn_del = QPushButton("✕")
        btn_del.setFixedWidth(32)
        btn_del.setFixedHeight(28)
        btn_del.setStyleSheet("background-color: #dc2626; color: white; border: none; border-radius: 4px;")
        btn_del.clicked.connect(lambda: self._remove_item_row(row_widget))

        bottom_row.addWidget(QLabel("Qté:"))
        bottom_row.addWidget(qty_spin)
        bottom_row.addWidget(price_label)
        bottom_row.addWidget(line_total_label)
        bottom_row.addStretch()
        bottom_row.addWidget(btn_del)

        row_layout.addLayout(top_row)
        row_layout.addLayout(bottom_row)

        # Store refs in the widget
        row_widget._mat_combo = mat_combo
        row_widget._unit_combo = unit_combo
        row_widget._qty_spin = qty_spin
        row_widget._price_label = price_label
        row_widget._line_total_label = line_total_label
        row_widget._stock_lbl = stock_lbl

        def update_units(idx):
            mat_id = mat_combo.currentData()
            mat = next((m for m in self.materials if m.id == mat_id), None)
            unit_combo.blockSignals(True)
            unit_combo.clear()
            if mat:
                unit_combo.addItem(f"{mat.unit} (principal) — {format_currency(mat.selling_price or 0)}/u", "primary")
                if mat.secondary_unit and mat.secondary_selling_price:
                    unit_combo.addItem(
                        f"{mat.secondary_unit} (détail) — {format_currency(mat.secondary_selling_price)}/u",
                        "secondary"
                    )
            else:
                unit_combo.addItem("-- unité --", "primary")
            unit_combo.blockSignals(False)
            update_price()

        def update_price():
            mat_id = mat_combo.currentData()
            mat = next((m for m in self.materials if m.id == mat_id), None)
            if mat:
                u_type = unit_combo.currentData()
                if u_type == "secondary" and mat.secondary_selling_price:
                    unit_price = mat.secondary_selling_price
                else:
                    unit_price = mat.selling_price or 0
                qty = qty_spin.value()
                total = unit_price * qty
                price_label.setText(f"{format_currency(unit_price)}/u")
                line_total_label.setText(f"= {format_currency(total)}")
            else:
                price_label.setText("0 DA/u")
                line_total_label.setText("= 0 DA")
            self._update_estimated_price()
            self._update_all_stocks()

        mat_combo.currentIndexChanged.connect(update_units)
        unit_combo.currentIndexChanged.connect(update_price)
        qty_spin.valueChanged.connect(update_price)

        self._item_rows.append(row_widget)
        # Insert before the stretch
        self.items_container.insertWidget(self.items_container.count() - 1, row_widget)
        
    def _update_all_stocks(self):
        # Calculate used quantities per material
        used_primary = {}
        
        for rw in self._item_rows:
            mat_id = rw._mat_combo.currentData()
            if not mat_id: continue
            
            mat = next((m for m in self.materials if m.id == mat_id), None)
            if not mat: continue
            
            u_type = rw._unit_combo.currentData()
            qty = rw._qty_spin.value()
            
            # Convert secondary to primary
            if u_type == "secondary" and mat.secondary_unit_qty and mat.secondary_unit_qty > 0:
                qty_in_primary = qty / mat.secondary_unit_qty
            else:
                qty_in_primary = qty
                
            used_primary[mat_id] = used_primary.get(mat_id, 0.0) + qty_in_primary

        # Update labels on all rows
        for rw in self._item_rows:
            mat_id = rw._mat_combo.currentData()
            if not mat_id:
                rw._stock_lbl.setText("")
                continue
                
            mat = next((m for m in self.materials if m.id == mat_id), None)
            if not mat: continue
            
            total_used = used_primary.get(mat_id, 0.0)
            remaining_primary = max(0, mat.quantity_available - total_used)
            
            if mat.secondary_unit and mat.secondary_unit_qty and mat.secondary_unit_qty > 0:
                # Format smartly (e.g. 46 feuilles et 3 m2)
                full_primary = int(remaining_primary)
                fraction = remaining_primary - full_primary
                sec_qty = round(fraction * mat.secondary_unit_qty, 2)
                
                if sec_qty > 0 and full_primary > 0:
                    text = f"Reste: {full_primary} {mat.unit} et {sec_qty:g} {mat.secondary_unit}"
                elif sec_qty > 0:
                    text = f"Reste: {sec_qty:g} {mat.secondary_unit}"
                else:
                    text = f"Reste: {full_primary} {mat.unit}"
            else:
                text = f"Reste: {remaining_primary:.1f} {mat.unit}"
                
            rw._stock_lbl.setText(text)

    def _remove_item_row(self, row_widget):
        if row_widget in self._item_rows:
            self._item_rows.remove(row_widget)
        self.items_container.removeWidget(row_widget)
        row_widget.deleteLater()
        self._update_estimated_price()
        self._update_all_stocks()

    def _update_estimated_price(self):
        total = 0.0
        for w in self._item_rows:
            if hasattr(w, '_mat_combo'):
                mat_id = w._mat_combo.currentData()
                mat = next((m for m in self.materials if m.id == mat_id), None)
                if mat:
                    u_type = w._unit_combo.currentData()
                    if u_type == "secondary" and mat.secondary_selling_price:
                        unit_price = mat.secondary_selling_price
                    else:
                        unit_price = mat.selling_price or 0
                    total += unit_price * w._qty_spin.value()
        self.est_price_label.setText(f"Total estimé (prix vente): {format_currency(total)}")

    def _validate(self):
        if not self.name_input.text().strip():
            show_error(self, "Validation", "Le nom du client est obligatoire")
            return
        self.accept()

    def get_data(self) -> dict:
        qdate = self.delivery_date.date()

        items = []
        for i in range(self.items_container.count()):
            w = self.items_container.itemAt(i).widget()
            if w and hasattr(w, '_mat_combo'):
                mat_id = w._mat_combo.currentData()
                mat = next((m for m in self.materials if m.id == mat_id), None)
                if mat:
                    u_type = w._unit_combo.currentData()
                    if u_type == "secondary" and mat.secondary_selling_price:
                        unit_price = mat.secondary_selling_price
                        unit = mat.secondary_unit
                    else:
                        unit_price = mat.selling_price or mat.purchase_cost
                        unit = mat.unit
                    items.append({
                        "material_id": mat.id,
                        "product_name": mat.designation,
                        "quantity": w._qty_spin.value(),
                        "dimensions": None,
                        "category": mat.category,
                        "unit_cost": unit_price,
                        "unit": unit,
                    })

        return {
            "customer_name": self.name_input.text().strip(),
            "customer_phone": self.phone_input.text().strip() or None,
            "customer_address": self.address_input.text().strip() or None,
            "expected_delivery_date": date(qdate.year(), qdate.month(), qdate.day()),
            "urgency": self.urgency_combo.currentData(),
            "notes": self.notes_input.toPlainText().strip() or None,
            "deposit_amount": self.deposit_spin.value(),
            "deposit_method": self.deposit_method.currentText(),
            "items": items,
        }
