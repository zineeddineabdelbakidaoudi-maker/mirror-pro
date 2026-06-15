"""Header component with page title, search, and datetime."""
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QLabel, QLineEdit, QPushButton,
)
from PySide6.QtCore import Qt, QTimer, Signal
from datetime import datetime


class Header(QWidget):
    search_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("header")
        self.setFixedHeight(56)
        self._setup_ui()
        self._start_clock()

    def _setup_ui(self):
        layout = QHBoxLayout(self)
        layout.setContentsMargins(24, 0, 24, 0)

        self.title_label = QLabel("Tableau de bord")
        self.title_label.setObjectName("page_title")
        layout.addWidget(self.title_label)

        layout.addStretch()

        # Search bar
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Rechercher...")
        self.search_input.setFixedWidth(250)
        self.search_input.setFixedHeight(36)
        self.search_input.textChanged.connect(self.search_changed.emit)
        layout.addWidget(self.search_input)

        layout.addStretch()

        # DateTime
        self.datetime_label = QLabel()
        self.datetime_label.setObjectName("datetime_label")
        layout.addWidget(self.datetime_label)

    def set_title(self, title: str):
        self.title_label.setText(title)

    def _start_clock(self):
        self._update_clock()
        timer = QTimer(self)
        timer.timeout.connect(self._update_clock)
        timer.start(30000)  # update every 30s

    def _update_clock(self):
        now = datetime.now()
        self.datetime_label.setText(now.strftime("%d/%m/%Y  %H:%M"))
