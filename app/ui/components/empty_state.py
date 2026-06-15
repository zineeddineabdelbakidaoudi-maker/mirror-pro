"""Empty state widget shown when a table/list has no data."""
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Qt
from app.ui.theme import Theme


class EmptyState(QWidget):
    def __init__(self, icon: str = "📭", message: str = "Aucune donnée",
                 sub_message: str = "", parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(8)

        icon_label = QLabel(icon)
        icon_label.setAlignment(Qt.AlignCenter)
        icon_label.setStyleSheet("font-size: 48px;")
        layout.addWidget(icon_label)

        msg_label = QLabel(message)
        msg_label.setAlignment(Qt.AlignCenter)
        t = Theme.instance().colors
        msg_label.setStyleSheet(f"font-size: 16px; color: {t.text_secondary}; font-weight: 500;")
        layout.addWidget(msg_label)

        if sub_message:
            sub_label = QLabel(sub_message)
            sub_label.setAlignment(Qt.AlignCenter)
            sub_label.setStyleSheet(f"font-size: 12px; color: {t.text_muted};")
            layout.addWidget(sub_label)
