"""Sidebar navigation component."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSpacerItem, QSizePolicy
from PySide6.QtCore import Signal
from app.utils.constants import SIDEBAR_ITEMS


SIDEBAR_ICONS = {
    "dashboard": "📊",
    "pos": "🛒",
    "orders": "📋",
    "clients": "👥",
    "debts": "🔴",
    "stock": "📦",
    "inventory": "📝",
    "suppliers": "🏭",
    "reports": "📈",
    "zakat": "🌙",
    "settings": "⚙️",
}


class Sidebar(QWidget):
    page_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sidebar")
        self.setFixedWidth(240)
        self.buttons = {}
        self.current_page = "dashboard"
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # App title
        title = QLabel("  ✦ MiroirPro")
        title.setObjectName("sidebar_title")
        title.setFixedHeight(60)
        layout.addWidget(title)

        # Navigation buttons
        for key, label, _ in SIDEBAR_ITEMS:
            icon = SIDEBAR_ICONS.get(key, "")
            btn = QPushButton(f"  {icon}  {label}")
            btn.setProperty("class", "sidebar_btn")
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(44)
            btn.clicked.connect(lambda checked, k=key: self._on_click(k))
            self.buttons[key] = btn
            layout.addWidget(btn)

        layout.addSpacerItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        # Theme toggle at bottom
        self.theme_btn = QPushButton("  🌙  Mode sombre")
        self.theme_btn.setProperty("class", "sidebar_btn")
        self.theme_btn.setCursor(Qt.PointingHandCursor)
        self.theme_btn.setFixedHeight(44)
        layout.addWidget(self.theme_btn)

        self._update_active()

    def _on_click(self, key: str):
        self.current_page = key
        self._update_active()
        self.page_changed.emit(key)

    def _update_active(self):
        for key, btn in self.buttons.items():
            btn.setProperty("active", "true" if key == self.current_page else "false")
            btn.style().unpolish(btn)
            btn.style().polish(btn)

    def set_active(self, key: str):
        self.current_page = key
        self._update_active()

    def update_theme_label(self, is_dark: bool):
        if is_dark:
            self.theme_btn.setText("  ☀️  Mode clair")
        else:
            self.theme_btn.setText("  🌙  Mode sombre")


from PySide6.QtCore import Qt
