"""Placeholder pages for modules to be fully built in later phases."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame
from PySide6.QtCore import Qt
from app.ui.components.empty_state import EmptyState


class PlaceholderPage(QWidget):
    """Base stub page with empty state message."""
    def __init__(self, title: str, icon: str = "🚧", message: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        es = EmptyState(icon, title, message or "Ce module sera disponible dans une prochaine mise à jour")
        layout.addWidget(es)

    def refresh(self):
        pass

    def filter(self, text: str):
        pass
