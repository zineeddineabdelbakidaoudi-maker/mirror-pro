"""Dashboard page — main overview with KPIs and recent activity."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QFrame,
)
from PySide6.QtCore import Qt, Signal
from app.ui.components.stat_card import StatCard
from app.ui.theme import Theme
from app.database.engine import get_session
from app.services.activity_service import ActivityService
from app.utils.formatters import format_currency, format_date


class DashboardPage(QWidget):
    navigate_requested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        self.layout_main = QVBoxLayout(container)
        self.layout_main.setContentsMargins(24, 24, 24, 24)
        self.layout_main.setSpacing(20)

        # KPI cards row
        self.cards_layout = QHBoxLayout()
        self.cards_layout.setSpacing(16)
        t = Theme.instance().colors

        self.card_revenue = StatCard("Revenus (Mois)", "0 DA", "💰", t.success)
        self.card_orders_pending = StatCard("Cmd. en cours", "0", "📋", t.accent)
        self.card_debts = StatCard("Dettes / Factures", "0", "🏭", t.danger)
        self.card_low_stock = StatCard("Alertes Stock", "0", "⚠️", t.warning)

        self.cards_layout.addWidget(self.card_revenue)
        self.cards_layout.addWidget(self.card_orders_pending)
        self.cards_layout.addWidget(self.card_debts)
        self.cards_layout.addWidget(self.card_low_stock)
        self.layout_main.addLayout(self.cards_layout)

        # Shortcuts Section
        shortcuts_layout = QHBoxLayout()
        shortcuts_layout.setSpacing(16)
        
        from PySide6.QtWidgets import QPushButton
        btn_pos = QPushButton("Vente Directe (POS)")
        btn_pos.setProperty("class", "primary")
        btn_pos.clicked.connect(lambda: self.navigate_requested.emit("pos"))
        
        btn_orders = QPushButton("Commandes")
        btn_orders.setProperty("class", "primary")
        btn_orders.clicked.connect(lambda: self.navigate_requested.emit("orders"))
        
        btn_stock = QPushButton("Stock")
        btn_stock.setProperty("class", "primary")
        btn_stock.clicked.connect(lambda: self.navigate_requested.emit("stock"))
        
        btn_reports = QPushButton("Rapports")
        btn_reports.setProperty("class", "primary")
        btn_reports.clicked.connect(lambda: self.navigate_requested.emit("reports"))
        
        shortcuts_layout.addWidget(btn_pos)
        shortcuts_layout.addWidget(btn_orders)
        shortcuts_layout.addWidget(btn_stock)
        shortcuts_layout.addWidget(btn_reports)
        self.layout_main.addLayout(shortcuts_layout)

        # Chart Section
        chart_layout = QVBoxLayout()
        chart_layout.setContentsMargins(0, 10, 0, 10)
        from app.ui.components.chart_widget import ChartWidget
        self.chart = ChartWidget()
        self.chart.setMinimumHeight(350)
        chart_layout.addWidget(self.chart)
        self.layout_main.addLayout(chart_layout)

        # Recent activity section
        activity_label = QLabel("Activité récente")
        activity_label.setProperty("class", "section_title")
        self.layout_main.addWidget(activity_label)

        self.activity_container = QVBoxLayout()
        self.activity_container.setSpacing(6)
        self.layout_main.addLayout(self.activity_container)

        self.layout_main.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def refresh(self):
        """Reload dashboard data from database."""
        session = get_session()
        try:
            from app.services.dashboard_service import DashboardService
            dash_svc = DashboardService(session)
            activity_svc = ActivityService(session)

            stats = dash_svc.get_summary_stats()
            self.card_revenue.set_value(format_currency(stats["monthly_revenue"]))
            self.card_orders_pending.set_value(str(stats["pending_orders"]))
            self.card_debts.set_value(str(stats["upcoming_debts"]))
            self.card_low_stock.set_value(str(stats["low_stock_alerts"]))

            # Refresh Chart
            chart_data = dash_svc.get_weekly_revenue_chart_data()
            self.chart.plot_bar_chart(
                labels=chart_data["labels"],
                values=chart_data["values"],
                title="Chiffre d'affaires (7 derniers jours)",
                color=Theme.instance().colors.accent
            )

            # Clear and reload activity
            while self.activity_container.count():
                item = self.activity_container.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            activities = activity_svc.get_recent(10)
            t = Theme.instance().colors
            if not activities:
                lbl = QLabel("  Aucune activité récente")
                lbl.setStyleSheet(f"color: {t.text_muted}; padding: 12px;")
                self.activity_container.addWidget(lbl)
            else:
                for act in activities:
                    frame = QFrame()
                    frame.setStyleSheet(f"""
                        background-color: {t.bg_card};
                        border: 1px solid {t.border};
                        border-radius: 6px;
                        padding: 10px 14px;
                    """)
                    row_layout = QHBoxLayout(frame)
                    row_layout.setContentsMargins(10, 6, 10, 6)
                    action_lbl = QLabel(f"● {act.action}")
                    action_lbl.setStyleSheet(f"color: {t.text_primary}; font-weight: 500;")
                    row_layout.addWidget(action_lbl)
                    if act.details:
                        detail_lbl = QLabel(act.details)
                        detail_lbl.setStyleSheet(f"color: {t.text_secondary}; font-size: 12px;")
                        row_layout.addWidget(detail_lbl)
                    row_layout.addStretch()
                    date_lbl = QLabel(format_date(act.created_at, include_time=True))
                    date_lbl.setStyleSheet(f"color: {t.text_muted}; font-size: 11px;")
                    row_layout.addWidget(date_lbl)
                    self.activity_container.addWidget(frame)
        finally:
            session.close()
