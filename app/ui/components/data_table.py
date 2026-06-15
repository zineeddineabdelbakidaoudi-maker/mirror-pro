"""Reusable data table component with sorting and selection."""
from PySide6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView
from PySide6.QtCore import Qt, Signal
from typing import List, Dict, Any, Optional


class DataTable(QTableWidget):
    row_selected = Signal(int)  # Emits the ID from column 0 (hidden)
    row_double_clicked = Signal(int)

    def __init__(self, columns: List[str], parent=None):
        super().__init__(parent)
        self.column_names = columns
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        self._setup()

    def setup_columns(self, columns: List[str]):
        self.column_names = columns
        self.clear()
        self.setColumnCount(len(columns))
        self.setHorizontalHeaderLabels(columns)
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(len(self.column_names)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        if len(self.column_names) > 1:
            header.setSectionResizeMode(len(self.column_names) - 1, QHeaderView.Stretch)

    def _setup(self):
        self.setAlternatingRowColors(False)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.verticalHeader().setVisible(False)
        self.setShowGrid(False)
        self.setSortingEnabled(True)

        # Stretch last column, resize others to contents
        header = self.horizontalHeader()
        header.setStretchLastSection(True)
        for i in range(len(self.column_names)):
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)
        if len(self.column_names) > 1:
            header.setSectionResizeMode(len(self.column_names) - 1, QHeaderView.Stretch)

        self.setVerticalScrollMode(QAbstractItemView.ScrollPerPixel)
        self.verticalHeader().setDefaultSectionSize(40)

        # Signals
        self.itemSelectionChanged.connect(self._on_selection)
        self.cellDoubleClicked.connect(self._on_double_click)

    def set_data(self, rows: List[List[Any]], id_column: int = 0):
        """Populate table with data. First column is typically the hidden ID."""
        self.setSortingEnabled(False)
        self.setRowCount(len(rows))
        for r, row in enumerate(rows):
            for c, value in enumerate(row):
                item = QTableWidgetItem(str(value) if value is not None else "")
                # Try numeric sorting for number-like values
                if isinstance(value, (int, float)):
                    item.setData(Qt.UserRole, value)
                item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
                self.setItem(r, c, item)
        self.setSortingEnabled(True)
        # Hide ID column
        if id_column >= 0:
            self.setColumnHidden(id_column, True)

    def _on_selection(self):
        rows = self.selectionModel().selectedRows()
        if rows:
            row = rows[0].row()
            id_item = self.item(row, 0)
            if id_item:
                try:
                    self.row_selected.emit(int(id_item.text()))
                except ValueError:
                    pass

    def _on_double_click(self, row, col):
        id_item = self.item(row, 0)
        if id_item:
            try:
                self.row_double_clicked.emit(int(id_item.text()))
            except ValueError:
                pass

    def get_selected_id(self) -> Optional[int]:
        rows = self.selectionModel().selectedRows()
        if rows:
            id_item = self.item(rows[0].row(), 0)
            if id_item:
                try:
                    return int(id_item.text())
                except ValueError:
                    return None
        return None

    def filter_rows(self, text: str):
        """Show only rows containing the search text."""
        text = text.lower()
        for row in range(self.rowCount()):
            visible = False
            for col in range(self.columnCount()):
                item = self.item(row, col)
                if item and text in item.text().lower():
                    visible = True
                    break
            self.setRowHidden(row, not visible)
