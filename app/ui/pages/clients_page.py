"""Clients page — browse clients, view orders/payments/debts, add payments."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QDialog, QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QLabel,
    QFrame, QScrollArea, QTabWidget, QSplitter, QSizePolicy, QTextEdit,
    QSpacerItem,
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QFont

from app.ui.components.data_table import DataTable
from app.ui.components.confirm_dialog import confirm_action, show_error, show_success
from app.ui.theme import Theme
from app.database.engine import get_session
from app.services.customer_service import CustomerService
from app.services.order_service import OrderService
from app.utils.formatters import format_currency, format_date
from app.ui.components.status_badge import STATUS_DISPLAY


# ══════════════════════════════════════════════════════════════════════════════
#  Helpers
# ══════════════════════════════════════════════════════════════════════════════

def _btn(text: str, cls: str = "", cursor=True) -> QPushButton:
    b = QPushButton(text)
    if cls:
        b.setProperty("class", cls)
    if cursor:
        b.setCursor(Qt.PointingHandCursor)
    return b


def _label(text: str, bold: bool = False, size: int = 0,
           color: str = "", wrap: bool = False) -> QLabel:
    lbl = QLabel(text)
    style_parts = []
    if bold:
        style_parts.append("font-weight: 600;")
    if size:
        style_parts.append(f"font-size: {size}px;")
    if color:
        style_parts.append(f"color: {color};")
    if style_parts:
        lbl.setStyleSheet(" ".join(style_parts))
    if wrap:
        lbl.setWordWrap(True)
    return lbl


def _separator(t) -> QFrame:
    sep = QFrame()
    sep.setFrameShape(QFrame.HLine)
    sep.setStyleSheet(f"border: none; background: {t.border}; max-height: 1px;")
    return sep


# ══════════════════════════════════════════════════════════════════════════════
#  ClientCard  (left-panel item)
# ══════════════════════════════════════════════════════════════════════════════

class ClientCard(QFrame):
    """Clickable card for the left-panel client list."""

    clicked = Signal(int)

    def __init__(self, customer, precomputed_debt: float = 0.0, parent=None):
        super().__init__(parent)
        self.customer_id = customer.id
        self._selected = False
        self._build(customer, precomputed_debt)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(72)
        self._apply_style(selected=False)

    # ── Build ──────────────────────────────────────────────
    def _build(self, customer, debt: float = 0.0):
        t = Theme.instance().colors
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(3)

        # Row 1: name
        name_lbl = QLabel(customer.name)
        font = QFont()
        font.setWeight(QFont.DemiBold)
        name_lbl.setFont(font)
        name_lbl.setStyleSheet(f"color: {t.text_primary}; font-size: 13px;")
        layout.addWidget(name_lbl)

        # Row 2: phone + debt badge
        row2 = QHBoxLayout()
        row2.setContentsMargins(0, 0, 0, 0)
        row2.setSpacing(6)

        phone_lbl = QLabel(customer.phone or "—")
        phone_lbl.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
        row2.addWidget(phone_lbl)
        row2.addStretch()

        # Debt badge (uses pre-computed value — no live DB call needed)
        if debt > 0:
            badge = QLabel(f"Créance: {format_currency(debt)}")
            badge.setStyleSheet(
                "background: #ef4444; color: #ffffff; border-radius: 8px;"
                "padding: 1px 6px; font-size: 10px; font-weight: 600;"
            )
            badge.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
            row2.addWidget(badge)

        layout.addLayout(row2)

    # ── Style ──────────────────────────────────────────────
    def _apply_style(self, selected: bool):
        t = Theme.instance().colors
        border = f"2px solid {t.accent}" if selected else f"1px solid {t.border}"
        self.setStyleSheet(f"""
            ClientCard {{
                background: {t.bg_card};
                border: {border};
                border-radius: 8px;
            }}
            ClientCard:hover {{
                background: {t.bg_hover};
            }}
        """)

    def set_selected(self, selected: bool):
        self._selected = selected
        self._apply_style(selected)

    # ── Events ─────────────────────────────────────────────
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.customer_id)
        super().mousePressEvent(event)


# ══════════════════════════════════════════════════════════════════════════════
#  ClientsPage
# ══════════════════════════════════════════════════════════════════════════════

class ClientsPage(QWidget):
    """Main clients page with split-panel layout."""

    open_order_detail = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._all_customers = []          # full list from DB
        self._current_customer_id = None  # selected customer
        self._cards: dict[int, ClientCard] = {}  # id -> card widget
        self._root_layout = None
        self._setup_ui()

    def update_theme(self):
        """Called by main_window when theme is toggled. Rebuilds the UI."""
        # Clear layout
        if self._root_layout is not None:
            QWidget().setLayout(self._root_layout) # Orphan the old layout
        self._cards.clear()
        self._setup_ui()
        if hasattr(self, 'refresh'):
            self.refresh()
        if self._current_customer_id:
            self._on_card_clicked(self._current_customer_id)

    # ══════════════════════════════════════════════════════════
    #  UI Setup
    # ══════════════════════════════════════════════════════════

    def _setup_ui(self):
        t = Theme.instance().colors
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        self._root_layout = root

        splitter = QSplitter(Qt.Horizontal)
        splitter.setHandleWidth(1)
        splitter.setStyleSheet(f"QSplitter::handle {{ background: {t.border}; }}")

        # ── Left panel ────────────────────────────────────
        left_widget = QWidget()
        left_widget.setObjectName("LeftPanel")
        left_widget.setFixedWidth(210)
        left_widget.setStyleSheet(f"QWidget#LeftPanel {{ background: {t.bg_secondary}; }}")
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(10, 14, 10, 14)
        left_layout.setSpacing(8)

        # Search bar
        self.search_bar = QLineEdit()
        self.search_bar.setPlaceholderText("🔍  Rechercher…")
        self.search_bar.setStyleSheet(f"""
            QLineEdit {{
                background: {t.bg_input};
                border: 1px solid {t.border};
                border-radius: 6px;
                padding: 6px 10px;
                color: {t.text_primary};
                font-size: 12px;
            }}
            QLineEdit:focus {{
                border-color: {t.accent};
            }}
        """)
        self.search_bar.textChanged.connect(self._on_search)
        left_layout.addWidget(self.search_bar)

        # Add button
        btn_new = _btn("+ Nouveau client", "primary")
        btn_new.clicked.connect(self._add_client)
        left_layout.addWidget(btn_new)

        # Count label
        self.count_label = QLabel("0 client(s)")
        self.count_label.setStyleSheet(
            f"color: {t.text_muted}; font-size: 11px; padding-left: 2px;"
        )
        left_layout.addWidget(self.count_label)

        left_layout.addWidget(_separator(t))

        # Scrollable card list
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
            f"QScrollBar:vertical {{ background: {t.bg_secondary}; width: 6px; border-radius: 3px; }}"
            f"QScrollBar::handle:vertical {{ background: {t.scrollbar}; border-radius: 3px; }}"
            f"QScrollBar::handle:vertical:hover {{ background: {t.scrollbar_hover}; }}"
            "QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }"
        )

        self.cards_container = QWidget()
        self.cards_container.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(self.cards_container)
        self.cards_layout.setContentsMargins(0, 4, 0, 4)
        self.cards_layout.setSpacing(6)
        self.cards_layout.addStretch()

        scroll.setWidget(self.cards_container)
        left_layout.addWidget(scroll, 1)

        splitter.addWidget(left_widget)

        # ── Right panel ───────────────────────────────────
        self.right_panel = QWidget()
        self.right_panel.setObjectName("RightPanel")
        self.right_panel.setStyleSheet(f"QWidget#RightPanel {{ background: {t.bg_primary}; }}")
        right_layout = QVBoxLayout(self.right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(0)

        # Empty state
        self.empty_state = self._build_empty_state(t)
        right_layout.addWidget(self.empty_state)

        # Detail area (hidden until a client is selected)
        self.detail_widget = QWidget()
        self.detail_widget.setVisible(False)
        detail_main = QVBoxLayout(self.detail_widget)
        detail_main.setContentsMargins(24, 20, 24, 20)
        detail_main.setSpacing(16)

        # Header card
        self.detail_header = self._build_detail_header(t, detail_main)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{
                border: 1px solid {t.border};
                border-radius: 8px;
                background: {t.bg_card};
            }}
            QTabBar::tab {{
                background: {t.bg_secondary};
                color: {t.text_secondary};
                border: 1px solid {t.border};
                border-bottom: none;
                padding: 8px 18px;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                margin-right: 2px;
                font-size: 13px;
            }}
            QTabBar::tab:selected {{
                background: {t.bg_card};
                color: {t.text_primary};
                font-weight: 600;
                border-bottom: 2px solid {t.accent};
            }}
            QTabBar::tab:hover:!selected {{
                background: {t.bg_hover};
            }}
        """)
        detail_main.addWidget(self.tabs, 1)

        # -- Commandes tab --
        tab_orders = QWidget()
        tab_orders_layout = QVBoxLayout(tab_orders)
        tab_orders_layout.setContentsMargins(12, 12, 12, 12)
        self.orders_table = DataTable(
            ["ID", "Réf", "Date", "Statut", "Prix final", "Payé", "Reste"]
        )
        self.orders_table.row_double_clicked.connect(self._on_open_order)
        tab_orders_layout.addWidget(self.orders_table)
        self.tabs.addTab(tab_orders, "📦  Commandes")

        # -- Paiements tab --
        tab_payments = QWidget()
        tab_payments_layout = QVBoxLayout(tab_payments)
        tab_payments_layout.setContentsMargins(12, 12, 12, 12)
        self.payments_table = DataTable(
            ["ID", "Date", "Commande", "Montant", "Mode", "Type"]
        )
        tab_payments_layout.addWidget(self.payments_table)
        self.tabs.addTab(tab_payments, "💳  Paiements")

        # -- Créances tab --
        tab_debts = QWidget()
        tab_debts_layout = QVBoxLayout(tab_debts)
        tab_debts_layout.setContentsMargins(12, 12, 12, 12)

        # Debt summary row
        self.debt_total_label = QLabel()
        self.debt_total_label.setStyleSheet(
            f"color: #ef4444; font-weight: 700; font-size: 14px; padding-bottom: 6px;"
        )
        tab_debts_layout.addWidget(self.debt_total_label)

        # Scrollable debt list
        debt_scroll = QScrollArea()
        debt_scroll.setWidgetResizable(True)
        debt_scroll.setStyleSheet(
            "QScrollArea { border: none; background: transparent; }"
        )
        self.debt_items_container = QWidget()
        self.debt_items_container.setStyleSheet("background: transparent;")
        self.debt_items_layout = QVBoxLayout(self.debt_items_container)
        self.debt_items_layout.setContentsMargins(0, 0, 0, 0)
        self.debt_items_layout.setSpacing(8)
        self.debt_items_layout.addStretch()
        debt_scroll.setWidget(self.debt_items_container)
        tab_debts_layout.addWidget(debt_scroll, 1)
        self.tabs.addTab(tab_debts, "🔴  Créances")

        right_layout.addWidget(self.detail_widget, 1)

        splitter.addWidget(self.right_panel)
        splitter.setSizes([210, 800])
        splitter.setCollapsible(0, False)
        splitter.setCollapsible(1, False)

        root.addWidget(splitter)

    def _build_empty_state(self, t) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        layout.setAlignment(Qt.AlignCenter)

        icon = QLabel("👤")
        icon.setStyleSheet("font-size: 48px;")
        icon.setAlignment(Qt.AlignCenter)
        layout.addWidget(icon)

        lbl = QLabel("Sélectionnez un client")
        lbl.setStyleSheet(
            f"color: {t.text_muted}; font-size: 16px; font-weight: 500;"
        )
        lbl.setAlignment(Qt.AlignCenter)
        layout.addWidget(lbl)

        hint = QLabel("Choisissez un client dans la liste de gauche\nou créez-en un nouveau.")
        hint.setStyleSheet(f"color: {t.text_muted}; font-size: 13px;")
        hint.setAlignment(Qt.AlignCenter)
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return w

    def _build_detail_header(self, t, parent_layout) -> dict:
        """Build and add the detail header card. Returns refs dict."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {t.bg_card};
                border: 1px solid {t.border};
                border-radius: 10px;
            }}
        """)
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(20, 16, 20, 16)
        card_layout.setSpacing(16)

        info_col = QVBoxLayout()
        info_col.setSpacing(4)

        self._header_name = QLabel("—")
        self._header_name.setStyleSheet(
            f"color: {t.text_primary}; font-size: 20px; font-weight: 700;"
        )
        info_col.addWidget(self._header_name)

        row_sub = QHBoxLayout()
        row_sub.setSpacing(16)

        self._header_phone = QLabel()
        self._header_phone.setStyleSheet(f"color: {t.text_secondary}; font-size: 13px;")
        row_sub.addWidget(self._header_phone)

        self._header_address = QLabel()
        self._header_address.setStyleSheet(f"color: {t.text_secondary}; font-size: 13px;")
        self._header_address.setWordWrap(True)
        row_sub.addWidget(self._header_address)
        row_sub.addStretch()

        info_col.addLayout(row_sub)

        self._header_debt = QLabel()
        self._header_debt.setStyleSheet(
            "background: #ef4444; color: #ffffff; border-radius: 8px;"
            "padding: 3px 10px; font-size: 12px; font-weight: 700;"
        )
        self._header_debt.setVisible(False)
        info_col.addWidget(self._header_debt, 0, Qt.AlignLeft)

        card_layout.addLayout(info_col, 1)

        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(8)

        btn_edit = _btn("✏  Modifier", "")
        btn_edit.setFixedWidth(110)
        btn_edit.clicked.connect(self._edit_client)
        btn_layout.addWidget(btn_edit)

        btn_delete = _btn("🗑  Supprimer", "danger")
        btn_delete.setFixedWidth(110)
        btn_delete.clicked.connect(self._delete_client)
        btn_layout.addWidget(btn_delete)
        btn_layout.setAlignment(Qt.AlignTop)
        card_layout.addLayout(btn_layout)

        parent_layout.addWidget(card)

    # ══════════════════════════════════════════════════════════
    #  Data / Refresh
    # ══════════════════════════════════════════════════════════

    def refresh(self):
        """Reload all data from database."""
        session = get_session()
        try:
            svc = CustomerService(session)
            customers = svc.get_all_customers()
            # Pre-compute debts while session is open (dynamic relationship needs it)
            self._all_customers = customers
            self._customer_debts: dict = {
                c.id: svc.get_total_debt(c.id) for c in customers
            }
        finally:
            session.close()

        self._rebuild_cards(self._all_customers)

        # Re-select current customer if still valid
        if self._current_customer_id:
            ids = {c.id for c in self._all_customers}
            if self._current_customer_id in ids:
                self._load_detail(self._current_customer_id)
            else:
                self._current_customer_id = None
                self._show_empty_state()

    def _rebuild_cards(self, customers):
        """Clear and rebuild client cards from a list of customers."""
        # Remove existing cards
        while self.cards_layout.count() > 1:  # keep stretch at end
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        self._cards.clear()
        t = Theme.instance().colors

        if not customers:
            no_result = QLabel("Aucun client trouvé")
            no_result.setStyleSheet(f"color: {t.text_muted}; font-size: 12px; padding: 10px;")
            no_result.setAlignment(Qt.AlignCenter)
            self.cards_layout.insertWidget(0, no_result)
            self.count_label.setText("0 client(s)")
            return

        # Use pre-computed debt cache (fallback to 0 if not available)
        debt_cache = getattr(self, "_customer_debts", {})

        for i, cust in enumerate(customers):
            card = ClientCard(cust, precomputed_debt=debt_cache.get(cust.id, 0.0))
            card.clicked.connect(self._on_card_clicked)
            if cust.id == self._current_customer_id:
                card.set_selected(True)
            self.cards_layout.insertWidget(i, card)
            self._cards[cust.id] = card

        self.count_label.setText(f"{len(customers)} client(s)")

    # ══════════════════════════════════════════════════════════
    #  Detail Panel
    # ══════════════════════════════════════════════════════════

    def _show_empty_state(self):
        self.empty_state.setVisible(True)
        self.detail_widget.setVisible(False)

    def _show_detail(self):
        self.empty_state.setVisible(False)
        self.detail_widget.setVisible(True)

    def _load_detail(self, customer_id: int):
        """Load all detail data for the selected customer."""
        session = get_session()
        try:
            svc = CustomerService(session)
            customer = svc.get_customer(customer_id)
            if not customer:
                self._show_empty_state()
                return

            # ── Header ──────────────────────────────────
            self._header_name.setText(customer.name)
            self._header_phone.setText(f"📞  {customer.phone}" if customer.phone else "")
            self._header_address.setText(f"📍  {customer.address}" if customer.address else "")
            debt = customer.total_remaining_debt
            if debt > 0:
                self._header_debt.setText(f"Créance totale: {format_currency(debt)}")
                self._header_debt.setVisible(True)
            else:
                self._header_debt.setVisible(False)

            # ── Commandes tab ───────────────────────────
            orders = svc.get_customer_orders(customer_id)
            order_rows = []
            for o in orders:
                order_rows.append([
                    o.id,
                    o.reference,
                    format_date(o.order_date),
                    STATUS_DISPLAY.get(o.status, o.status),
                    format_currency(o.final_selling_price),
                    format_currency(o.total_payments),
                    format_currency(o.remaining_balance) if o.final_selling_price else "—",
                ])
            self.orders_table.set_data(order_rows)

            # ── Paiements tab ───────────────────────────
            payments = svc.get_customer_payments(customer_id)
            pay_rows = []
            for p in payments:
                ref = p.order.reference if p.order else "—"
                pay_rows.append([
                    p.id,
                    format_date(p.payment_date, include_time=True),
                    ref,
                    format_currency(p.amount),
                    p.payment_method or "—",
                    p.payment_type or "—",
                ])
            self.payments_table.set_data(pay_rows)

            # ── Créances tab ────────────────────────────
            self._rebuild_debt_tab(svc, customer_id)

        finally:
            session.close()

        self._show_detail()

    def _rebuild_debt_tab(self, svc: CustomerService, customer_id: int):
        """Rebuild the debt items in the Créances tab."""
        t = Theme.instance().colors

        # Clear existing items
        while self.debt_items_layout.count() > 1:
            item = self.debt_items_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        debts = svc.get_customer_debts(customer_id)
        if not debts:
            self.debt_total_label.setText("Aucune créance")
            self.debt_total_label.setStyleSheet(
                f"color: {t.success}; font-weight: 700; font-size: 14px; padding-bottom: 6px;"
            )
            no_debt = QLabel("✅  Ce client n'a aucune créance en attente.")
            no_debt.setStyleSheet(f"color: {t.text_muted}; font-size: 13px; padding: 12px;")
            self.debt_items_layout.insertWidget(0, no_debt)
            return

        total_debt = sum(o.remaining_balance for o in debts)
        self.debt_total_label.setText(
            f"Total des créances: {format_currency(total_debt)}"
        )
        self.debt_total_label.setStyleSheet(
            "color: #ef4444; font-weight: 700; font-size: 14px; padding-bottom: 6px;"
        )

        for i, order in enumerate(debts):
            row_card = self._build_debt_row(order, t)
            self.debt_items_layout.insertWidget(i, row_card)

    def _build_debt_row(self, order, t) -> QFrame:
        """Build a single debt row card."""
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background: {t.danger_bg};
                border: 1px solid #ef4444;
                border-radius: 8px;
            }}
        """)
        row = QHBoxLayout(card)
        row.setContentsMargins(14, 10, 14, 10)
        row.setSpacing(16)

        # Ref + date
        info = QVBoxLayout()
        info.setSpacing(2)
        ref_lbl = QLabel(order.reference)
        ref_lbl.setStyleSheet(
            f"color: {t.text_primary}; font-size: 13px; font-weight: 700;"
        )
        info.addWidget(ref_lbl)
        date_lbl = QLabel(format_date(order.order_date))
        date_lbl.setStyleSheet(f"color: {t.text_secondary}; font-size: 11px;")
        info.addWidget(date_lbl)
        row.addLayout(info)

        row.addStretch()

        # Amounts
        amounts_col = QVBoxLayout()
        amounts_col.setSpacing(2)

        def amount_lbl(label: str, value: str, danger: bool = False) -> QLabel:
            color = "#ef4444" if danger else t.text_secondary
            l = QLabel(f"{label}: {value}")
            l.setStyleSheet(f"color: {color}; font-size: 12px;")
            return l

        amounts_col.addWidget(amount_lbl("Prix", format_currency(order.final_selling_price)))
        amounts_col.addWidget(amount_lbl("Payé", format_currency(order.total_payments)))
        amounts_col.addWidget(amount_lbl("Reste", format_currency(order.remaining_balance), danger=True))
        row.addLayout(amounts_col)

        # Versement button
        btn_pay = _btn("+ Versement", "primary")
        btn_pay.setFixedWidth(110)
        btn_pay.clicked.connect(lambda _, oid=order.id: self._add_payment(oid))
        row.addWidget(btn_pay)

        return card

    # ══════════════════════════════════════════════════════════
    #  Filtering
    # ══════════════════════════════════════════════════════════

    def filter(self, text: str):
        """Filter the client list by search text (from header search bar)."""
        self._on_search(text)

    def _on_search(self, text: str):
        text = text.strip().lower()
        if not text:
            filtered = self._all_customers
        else:
            filtered = [
                c for c in self._all_customers
                if text in c.name.lower()
                or (c.phone and text in c.phone.lower())
            ]
        self._rebuild_cards(filtered)

    # ══════════════════════════════════════════════════════════
    #  Slot handlers
    # ══════════════════════════════════════════════════════════

    def _on_card_clicked(self, customer_id: int):
        # Deselect previous
        if self._current_customer_id and self._current_customer_id in self._cards:
            self._cards[self._current_customer_id].set_selected(False)

        self._current_customer_id = customer_id

        if customer_id in self._cards:
            self._cards[customer_id].set_selected(True)

        self._load_detail(customer_id)

    def _on_open_order(self, order_id: int):
        self.open_order_detail.emit(order_id)

    # ══════════════════════════════════════════════════════════
    #  Actions
    # ══════════════════════════════════════════════════════════

    def _add_client(self):
        dlg = NewClientDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = get_session()
            try:
                svc = CustomerService(session)
                svc.create_customer(**data)
                show_success(self, "Succès", "Client ajouté avec succès.")
                self.refresh()
            except ValueError as e:
                show_error(self, "Erreur de validation", str(e))
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _edit_client(self):
        if not self._current_customer_id:
            return
        dlg = EditClientDialog(self, self._current_customer_id)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = get_session()
            try:
                svc = CustomerService(session)
                svc.update_customer(self._current_customer_id, **data)
                show_success(self, "Succès", "Client modifié avec succès.")
                self.refresh()
            except ValueError as e:
                show_error(self, "Erreur de validation", str(e))
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _delete_client(self):
        if not self._current_customer_id:
            return
        if not confirm_action(self, "Supprimer le client",
                              "Voulez-vous vraiment supprimer ce client ?\nToutes ses commandes et informations associées seront marquées comme supprimées."):
            return
        
        session = get_session()
        try:
            svc = CustomerService(session)
            svc.delete_customer(self._current_customer_id)
            show_success(self, "Succès", "Client supprimé avec succès.")
            self._current_customer_id = None
            self.refresh()
            self._show_empty_state()
        except ValueError as e:
            show_error(self, "Erreur", str(e))
        except Exception as e:
            show_error(self, "Erreur système", str(e))
        finally:
            session.close()

    def _add_payment(self, order_id: int):
        """Open AddPaymentDialog for a specific order."""
        if not self._current_customer_id:
            return
        session = get_session()
        try:
            svc = CustomerService(session)
            debts = svc.get_customer_debts(self._current_customer_id)
            
            dlg = AddPaymentDialog(self, order_id, debts)
            if dlg.exec() == QDialog.Accepted:
                data = dlg.get_data()
                svc.add_payment_to_order(
                    order_id=data["order_id"],
                    amount=data["amount"],
                    method=data["method"],
                    notes=data["notes"],
                )
                show_success(self, "Succès", "Paiement enregistré.")
                self._load_detail(self._current_customer_id)
                # Rebuild left-panel card debt badge
                self.refresh()
        except ValueError as e:
            show_error(self, "Erreur de validation", str(e))
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()


# ══════════════════════════════════════════════════════════════════════════════
#  Dialogs
# ══════════════════════════════════════════════════════════════════════════════

def _dialog_buttons(dialog: QDialog, save_text: str = "Enregistrer") -> QHBoxLayout:
    """Return a standard Cancel / Save button row."""
    row = QHBoxLayout()
    row.setSpacing(8)
    btn_cancel = QPushButton("Annuler")
    btn_cancel.clicked.connect(dialog.reject)
    btn_cancel.setCursor(Qt.PointingHandCursor)
    row.addStretch()
    row.addWidget(btn_cancel)
    btn_save = QPushButton(save_text)
    btn_save.setProperty("class", "primary")
    btn_save.clicked.connect(dialog.accept)
    btn_save.setCursor(Qt.PointingHandCursor)
    row.addWidget(btn_save)
    return row


class NewClientDialog(QDialog):
    """Dialog for creating a new client."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nouveau client")
        self.setMinimumWidth(420)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Nouveau client")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom complet *")
        form.addRow("Nom *:", self.name_input)

        self.phone_input = QLineEdit()
        self.phone_input.setPlaceholderText("0555 XXX XXX")
        form.addRow("Téléphone:", self.phone_input)

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("Adresse (optionnel)")
        form.addRow("Adresse:", self.address_input)

        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes internes (optionnel)")
        self.notes_input.setFixedHeight(70)
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)
        layout.addLayout(_dialog_buttons(self, "Créer le client"))

    def get_data(self) -> dict:
        return {
            "name": self.name_input.text().strip(),
            "phone": self.phone_input.text().strip() or None,
            "address": self.address_input.text().strip() or None,
            "notes": self.notes_input.toPlainText().strip() or None,
        }

    def accept(self):
        if not self.name_input.text().strip():
            show_error(self, "Validation", "Le nom du client est obligatoire.")
            return
        super().accept()


class EditClientDialog(QDialog):
    """Dialog for editing an existing client (pre-filled)."""

    def __init__(self, parent=None, customer_id: int = None):
        super().__init__(parent)
        self.customer_id = customer_id
        self.setWindowTitle("Modifier le client")
        self.setMinimumWidth(420)
        self._setup_ui()
        if customer_id:
            self._load()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Modifier le client")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        self.name_input = QLineEdit()
        form.addRow("Nom *:", self.name_input)

        self.phone_input = QLineEdit()
        form.addRow("Téléphone:", self.phone_input)

        self.address_input = QLineEdit()
        form.addRow("Adresse:", self.address_input)

        self.notes_input = QTextEdit()
        self.notes_input.setFixedHeight(70)
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)
        layout.addLayout(_dialog_buttons(self, "Enregistrer"))

    def _load(self):
        session = get_session()
        try:
            svc = CustomerService(session)
            cust = svc.get_customer(self.customer_id)
            if cust:
                self.name_input.setText(cust.name)
                self.phone_input.setText(cust.phone or "")
                self.address_input.setText(cust.address or "")
                self.notes_input.setText(cust.notes or "")
        finally:
            session.close()

    def get_data(self) -> dict:
        return {
            "name": self.name_input.text().strip(),
            "phone": self.phone_input.text().strip() or None,
            "address": self.address_input.text().strip() or None,
            "notes": self.notes_input.toPlainText().strip() or None,
        }

    def accept(self):
        if not self.name_input.text().strip():
            show_error(self, "Validation", "Le nom du client est obligatoire.")
            return
        super().accept()


class AddPaymentDialog(QDialog):
    """Dialog for adding a payment to an order with remaining balance."""

    def __init__(self, parent=None, preselect_order_id: int = None, debt_orders=None):
        super().__init__(parent)
        self._preselect_order_id = preselect_order_id
        self._debt_orders = debt_orders or []
        self.setWindowTitle("Enregistrer un versement")
        self.setMinimumWidth(440)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(14)

        title = QLabel("Nouveau versement")
        title.setStyleSheet("font-size: 16px; font-weight: 700;")
        layout.addWidget(title)

        form = QFormLayout()
        form.setSpacing(10)
        form.setLabelAlignment(Qt.AlignRight)

        # Order selector
        self.order_combo = QComboBox()
        for order in self._debt_orders:
            label = f"{order.reference}  — Reste: {format_currency(order.remaining_balance)}"
            self.order_combo.addItem(label, order.id)
        # Pre-select
        if self._preselect_order_id:
            for i in range(self.order_combo.count()):
                if self.order_combo.itemData(i) == self._preselect_order_id:
                    self.order_combo.setCurrentIndex(i)
                    break
        self.order_combo.currentIndexChanged.connect(self._update_max_amount)
        form.addRow("Commande *:", self.order_combo)

        # Amount
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 99_999_999)
        self.amount_spin.setDecimals(2)
        self.amount_spin.setSuffix("  DA")
        self.amount_spin.setGroupSeparatorShown(True)
        form.addRow("Montant (DA) *:", self.amount_spin)

        # Mode
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["espèces", "chèque", "virement", "autre"])
        form.addRow("Mode de paiement:", self.mode_combo)

        # Notes
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("Notes (optionnel)")
        form.addRow("Notes:", self.notes_input)

        layout.addLayout(form)

        # Helper label
        self.max_label = QLabel()
        self.max_label.setStyleSheet("color: #ef4444; font-size: 11px;")
        layout.addWidget(self.max_label)

        layout.addLayout(_dialog_buttons(self, "Enregistrer le paiement"))
        self._update_max_amount()

    def _update_max_amount(self):
        idx = self.order_combo.currentIndex()
        if idx < 0 or not self._debt_orders:
            return
        order_id = self.order_combo.currentData()
        order = next((o for o in self._debt_orders if o.id == order_id), None)
        if order:
            remaining = order.remaining_balance
            self.amount_spin.setMaximum(remaining)
            self.amount_spin.setValue(remaining)
            self.max_label.setText(f"Montant maximal: {format_currency(remaining)}")

    def get_data(self) -> dict:
        return {
            "order_id": self.order_combo.currentData(),
            "amount": self.amount_spin.value(),
            "method": self.mode_combo.currentText(),
            "notes": self.notes_input.text().strip() or None,
        }

    def accept(self):
        if self.amount_spin.value() <= 0:
            show_error(self, "Validation", "Le montant doit être supérieur à 0.")
            return
        if self.order_combo.currentData() is None:
            show_error(self, "Validation", "Veuillez sélectionner une commande.")
            return
        super().accept()
