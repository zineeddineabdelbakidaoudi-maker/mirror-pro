"""Point of Sale (POS) page for fast direct sales."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QFrame,
    QScrollArea, QGridLayout, QComboBox, QDoubleSpinBox, QSplitter
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from app.ui.components.confirm_dialog import show_error, show_success
from app.database.engine import get_session
from app.services.pos_service import PosService
from app.utils.formatters import format_currency

class PosPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.products = []
        self.cart = []  # List of dicts: product, qty
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(16)

        splitter = QSplitter(Qt.Horizontal)
        layout.addWidget(splitter)

        # ── Left Panel (Catalog) ──────────────────────────────────────────
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)

        catalog_title = QLabel("Catalogue (Produits en vente directe)")
        catalog_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        left_layout.addWidget(catalog_title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        self.grid_widget = QWidget()
        self.grid_layout = QGridLayout(self.grid_widget)
        self.grid_layout.setSpacing(12)
        scroll.setWidget(self.grid_widget)
        left_layout.addWidget(scroll)

        splitter.addWidget(left_panel)

        # ── Right Panel (Cart & Checkout) ─────────────────────────────────
        right_panel = QFrame()
        right_panel.setObjectName("cart_panel")
        right_panel.setStyleSheet("#cart_panel { background-color: var(--bg-card); border-radius: 8px; border: 1px solid var(--border); }")
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(16, 16, 16, 16)

        cart_title = QLabel("Panier Actuel")
        cart_title.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(cart_title)

        self.cart_table = QTableWidget(0, 4)
        self.cart_table.setHorizontalHeaderLabels(["Produit", "Qté", "Prix", ""])
        self.cart_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.cart_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.cart_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.cart_table.setSelectionMode(QTableWidget.NoSelection)
        right_layout.addWidget(self.cart_table)

        # Totals
        self.total_label = QLabel("Total: 0 DA")
        self.total_label.setStyleSheet("font-size: 20px; font-weight: bold; color: var(--accent); margin-top: 10px;")
        self.total_label.setAlignment(Qt.AlignRight)
        right_layout.addWidget(self.total_label)

        # Payment options
        payment_layout = QHBoxLayout()
        payment_layout.addWidget(QLabel("Moyen:"))
        self.payment_combo = QComboBox()
        self.payment_combo.addItems(["espèces", "carte", "chèque"])
        payment_layout.addWidget(self.payment_combo)
        right_layout.addLayout(payment_layout)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_clear = QPushButton("Vider")
        btn_clear.clicked.connect(self._clear_cart)
        btn_layout.addWidget(btn_clear)

        btn_checkout = QPushButton("Encaisser")
        btn_checkout.setProperty("class", "success")
        btn_checkout.setMinimumHeight(40)
        btn_checkout.clicked.connect(self._checkout)
        btn_layout.addWidget(btn_checkout, stretch=2)
        right_layout.addLayout(btn_layout)

        splitter.addWidget(right_panel)
        splitter.setSizes([700, 350])

    def refresh(self):
        self._load_products()
        self._render_catalog()

    def _load_products(self):
        session = get_session()
        try:
            svc = PosService(session)
            self.products = svc.get_pos_products()
        finally:
            session.close()

    def _render_catalog(self):
        # Clear grid
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 3
        row, col = 0, 0
        for p in self.products:
            card = self._create_product_card(p)
            self.grid_layout.addWidget(card, row, col)
            col += 1
            if col >= cols:
                col = 0
                row += 1

        self.grid_layout.setRowStretch(row + 1, 1)

    def _create_product_card(self, product):
        frame = QFrame()
        frame.setObjectName("pcard")
        frame.setStyleSheet("""
            #pcard {
                background-color: var(--bg-card);
                border: 1px solid var(--border);
                border-radius: 8px;
            }
            #pcard:hover { border-color: var(--primary); }
        """)
        layout = QVBoxLayout(frame)
        
        name_lbl = QLabel(product.name)
        name_lbl.setWordWrap(True)
        name_lbl.setStyleSheet("font-weight: bold; font-size: 14px;")
        
        stock_text = f"{product.quantity_on_hand} en stock" if product.stock_tracked else "Service"
        stock_color = "var(--danger)" if (product.stock_tracked and product.quantity_on_hand <= 0) else "var(--text-secondary)"
        stock_lbl = QLabel(stock_text)
        stock_lbl.setStyleSheet(f"color: {stock_color}; font-size: 11px;")
        
        price_lbl = QLabel(format_currency(product.selling_price))
        price_lbl.setStyleSheet("color: var(--primary); font-weight: bold;")
        
        layout.addWidget(name_lbl)
        layout.addWidget(stock_lbl)
        layout.addWidget(price_lbl)
        
        btn = QPushButton("Ajouter")
        if product.stock_tracked and product.quantity_on_hand <= 0:
            btn.setEnabled(False)
            btn.setText("Rupture")
        else:
            btn.clicked.connect(lambda _, p=product: self._add_to_cart(p))
            
        layout.addWidget(btn)
        return frame

    def _add_to_cart(self, product):
        # Check if exists
        existing = next((i for i in self.cart if i['product'].id == product.id), None)
        if existing:
            # Check stock limit
            if product.stock_tracked and existing['qty'] >= product.quantity_on_hand:
                show_error(self, "Stock", "Pas assez de stock disponible")
                return
            existing['qty'] += 1
        else:
            if product.stock_tracked and product.quantity_on_hand < 1:
                return
            self.cart.append({'product': product, 'qty': 1})
            
        self._update_cart_ui()

    def _remove_from_cart(self, idx):
        if 0 <= idx < len(self.cart):
            self.cart.pop(idx)
            self._update_cart_ui()

    def _update_qty(self, idx, val):
        if 0 <= idx < len(self.cart):
            p = self.cart[idx]['product']
            if p.stock_tracked and val > p.quantity_on_hand:
                show_error(self, "Stock", "Pas assez de stock disponible")
                # Need to reset spinbox to previous value in a real scenario
                # for now, we just cap it and re-render
                self.cart[idx]['qty'] = int(p.quantity_on_hand)
                self._update_cart_ui()
                return
            self.cart[idx]['qty'] = val
            self._update_totals()

    def _update_cart_ui(self):
        self.cart_table.setRowCount(0)
        total = 0.0
        
        for i, item in enumerate(self.cart):
            self.cart_table.insertRow(i)
            p = item['product']
            
            # Name
            self.cart_table.setItem(i, 0, QTableWidgetItem(p.name))
            
            # Qty SpinBox
            spin = QDoubleSpinBox()
            spin.setRange(1, 9999)
            spin.setDecimals(0)
            spin.setValue(item['qty'])
            spin.valueChanged.connect(lambda val, idx=i: self._update_qty(idx, int(val)))
            self.cart_table.setCellWidget(i, 1, spin)
            
            # Price
            price = p.selling_price * item['qty']
            total += price
            self.cart_table.setItem(i, 2, QTableWidgetItem(f"{price:,.0f} DA"))
            
            # Remove btn
            btn_del = QPushButton("Supprimer")
            btn_del.setProperty("class", "danger")
            btn_del.clicked.connect(lambda _, idx=i: self._remove_from_cart(idx))
            self.cart_table.setCellWidget(i, 3, btn_del)

        self._update_totals()

    def _update_totals(self):
        total = sum(i['product'].selling_price * i['qty'] for i in self.cart)
        self.total_label.setText(f"Total: {format_currency(total)}")

    def _clear_cart(self):
        self.cart.clear()
        self._update_cart_ui()

    def _checkout(self):
        if not self.cart:
            show_error(self, "Panier vide", "Veuillez ajouter des produits")
            return
            
        session = get_session()
        try:
            svc = PosService(session)
            items_data = [
                {"product_id": i['product'].id, "quantity": i['qty'], "unit_price": i['product'].selling_price}
                for i in self.cart
            ]
            
            sale = svc.process_sale(items_data, payment_method=self.payment_combo.currentText())
            
            show_success(self, "Vente réussie", f"Vente {sale.reference} enregistrée.")
            self._clear_cart()
            self.refresh()  # refresh catalog stocks
            
            # Print receipt
            self._print_sale_receipt(sale.id)
            
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _print_sale_receipt(self, sale_id):
        session = get_session()
        try:
            from app.printing.printer_manager import PrinterManager
            from app.services.settings_service import SettingsService
            from app.models.sale import Sale
            
            sale = session.query(Sale).get(sale_id)
            if not sale: return
            
            pm = PrinterManager(session)
            ss = SettingsService(session)
            
            # Build order_data dict expected by printer manager
            data = {
                "reference": sale.reference,
                "customer": "Client Passager",
                "date": sale.sale_date.strftime("%d/%m/%Y"),
                "items": [{"product_name": i.product_name, "quantity": i.quantity} for i in sale.items],
                "final_selling_price": sale.total_amount,
                "total_payments": sale.total_amount,
                "remaining_balance": 0
            }
            
            company = {
                "name": ss.get_company_name(), "phone": ss.get_company_phone(),
                "address": ss.get_company_address(), "footer": ss.get_receipt_footer(),
            }
            
            path = pm.print_customer_receipt(data, company)
            if path:
                import os; os.startfile(path)
        except Exception as e:
            show_error(self, "Erreur Impression", str(e))
        finally:
            session.close()
            
    def filter(self, text: str):
        # Filter products
        text = text.lower()
        # Repopulate layout based on filtered
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        cols = 3
        row, col = 0, 0
        for p in self.products:
            if text in p.name.lower() or text in p.category.lower():
                card = self._create_product_card(p)
                self.grid_layout.addWidget(card, row, col)
                col += 1
                if col >= cols:
                    col = 0
                    row += 1

        self.grid_layout.setRowStretch(row + 1, 1)
