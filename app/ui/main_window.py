"""Main application window with sidebar navigation and page stack."""
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout, QStackedWidget,
)
from PySide6.QtCore import Qt
from app.ui.theme import Theme
from app.ui.styles import get_stylesheet
from app.ui.components.sidebar import Sidebar
from app.ui.components.header import Header
from app.ui.pages.dashboard_page import DashboardPage
from app.ui.pages.stock_page import StockPage
from app.ui.pages.orders_page import OrdersPage
from app.ui.pages.order_detail_page import OrderDetailPage
from app.ui.pages.settings_page import SettingsPage
from app.ui.pages.pos_page import PosPage
from app.ui.pages.suppliers_page import SuppliersPage
from app.ui.pages.reports_page import ReportsPage
from app.ui.pages.inventory_page import InventoryPage
from app.ui.pages.zakat_page import ZakatPage
from app.ui.pages.clients_page import ClientsPage
from app.ui.pages.debts_page import DebtsPage


PAGE_TITLES = {
    "dashboard": "Tableau de bord",
    "pos": "POS / Vente directe",
    "orders": "Commandes",
    "clients": "Clients",
    "debts": "Créances Globales",
    "stock": "Stock",
    "inventory": "Inventaire",
    "suppliers": "Fournisseurs & Dettes",
    "reports": "Rapports",
    "zakat": "Zakat",
    "settings": "Paramètres",
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MiroirPro — Gestion Atelier")
        self.setMinimumSize(1200, 750)
        self.resize(1400, 850)
        self._setup_ui()
        self._apply_theme()
        self._navigate("dashboard")

    def _setup_ui(self):
        central = QWidget()
        central.setObjectName("central")
        self.setCentralWidget(central)

        main_layout = QHBoxLayout(central)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Sidebar
        self.sidebar = Sidebar()
        self.sidebar.page_changed.connect(self._navigate)
        self.sidebar.theme_btn.clicked.connect(self._toggle_theme)
        main_layout.addWidget(self.sidebar)

        # Right panel: header + content
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(0)

        self.header = Header()
        self.header.search_changed.connect(self._on_search)
        right.addWidget(self.header)

        # Page stack
        self.stack = QStackedWidget()
        self.pages = {}

        # Pages
        self.pages["dashboard"] = DashboardPage()
        self.pages["dashboard"].navigate_requested.connect(self._navigate)
        self.pages["pos"] = PosPage()
        self.pages["orders"] = OrdersPage()
        self.pages["order_detail"] = OrderDetailPage()
        self.pages["clients"] = ClientsPage()
        self.pages["debts"] = DebtsPage()
        self.pages["stock"] = StockPage()
        self.pages["inventory"] = InventoryPage()
        self.pages["suppliers"] = SuppliersPage()
        self.pages["reports"] = ReportsPage()
        self.pages["zakat"] = ZakatPage()
        self.pages["settings"] = SettingsPage()

        for page in self.pages.values():
            self.stack.addWidget(page)

        # Wire order navigation
        self.pages["orders"].open_order_detail.connect(self._open_order_detail)
        self.pages["order_detail"].back_requested.connect(lambda: self._navigate("orders"))
        self.pages["clients"].open_order_detail.connect(self._open_order_detail)
        
        # Wire customer navigation from debts
        self.pages["debts"].open_customer_detail.connect(self._open_customer_detail)

        right.addWidget(self.stack)
        main_layout.addLayout(right)

    def _navigate(self, page_key: str):
        if page_key not in self.pages:
            return
        self.stack.setCurrentWidget(self.pages[page_key])
        self.header.set_title(PAGE_TITLES.get(page_key, page_key))
        self.sidebar.set_active(page_key)

        # Refresh the page data
        page = self.pages[page_key]
        if hasattr(page, "refresh"):
            page.refresh()

    def _open_order_detail(self, order_id: int):
        self.pages["order_detail"].load_order(order_id)
        self._navigate("order_detail")
        
    def _open_customer_detail(self, customer_id: int):
        self._navigate("clients")
        # Ensure it selects the specific customer if the clients page handles it
        # Note: In clients_page.py, we might need a method to select a customer directly.
        # But we'll just navigate to clients page for now.
        if hasattr(self.pages["clients"], "_on_card_clicked"):
            self.pages["clients"]._on_card_clicked(customer_id)

    def _on_search(self, text: str):
        current = self.stack.currentWidget()
        if hasattr(current, "filter"):
            current.filter(text)

    def _toggle_theme(self):
        theme = Theme.instance()
        theme.toggle()
        self._apply_theme()
        self.sidebar.update_theme_label(theme.is_dark)

    def _apply_theme(self):
        self.setStyleSheet(get_stylesheet())
        # Force refresh inline styles on pages if supported
        for page in self.pages.values():
            if hasattr(page, "update_theme"):
                page.update_theme()
