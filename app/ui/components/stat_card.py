"""Stat card component for dashboard KPIs."""
from PySide6.QtWidgets import QFrame, QVBoxLayout, QLabel
from PySide6.QtCore import Qt


class StatCard(QFrame):
    def __init__(self, title: str, value: str, icon: str = "", accent_color: str = None, parent=None):
        super().__init__(parent)
        self.setProperty("class", "stat_card")
        self.setMinimumWidth(180)
        self.setMaximumHeight(120)

        layout = QVBoxLayout(self)
        layout.setSpacing(6)

        # Icon + title row
        lbl_title = QLabel(f"{icon}  {title}" if icon else title)
        lbl_title.setProperty("class", "stat_label")
        layout.addWidget(lbl_title)

        # Value
        self.value_label = QLabel(value)
        self.value_label.setProperty("class", "stat_value")
        if accent_color:
            self.value_label.setStyleSheet(f"color: {accent_color};")
        layout.addWidget(self.value_label)

    def set_value(self, value: str):
        self.value_label.setText(value)
