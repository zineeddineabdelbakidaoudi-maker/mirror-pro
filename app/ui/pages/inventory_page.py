"""Inventory page — physical stock count sessions."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QInputDialog, QDialog, QFormLayout, QDoubleSpinBox, QLineEdit, QSplitter
)
from PySide6.QtCore import Qt
from app.database.engine import get_session
from app.services.inventory_service import InventoryService
from app.ui.components.data_table import DataTable
from app.ui.components.confirm_dialog import show_error, show_success, confirm_action
from app.utils.formatters import format_date

class InventoryPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_session_id = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QLabel("Sessions d'Inventaire")
        title.setProperty("class", "page_title")
        layout.addWidget(title)

        toolbar = QHBoxLayout()
        btn_add = QPushButton("+ Nouvelle Session")
        btn_add.setProperty("class", "primary")
        btn_add.clicked.connect(self._new_session)
        toolbar.addWidget(btn_add)
        toolbar.addStretch()
        layout.addLayout(toolbar)

        # Splitter: Sessions on left, Lines on right
        splitter = QSplitter(Qt.Horizontal)

        # Sessions Table
        sess_container = QWidget()
        sess_layout = QVBoxLayout(sess_container)
        sess_layout.setContentsMargins(0,0,0,0)
        self.sessions_table = DataTable(["ID", "Nom", "Date", "Statut"])
        self.sessions_table.row_selected.connect(self._on_session_selected)
        sess_layout.addWidget(self.sessions_table)
        splitter.addWidget(sess_container)

        # Session Lines
        lines_container = QWidget()
        lines_layout = QVBoxLayout(lines_container)
        lines_layout.setContentsMargins(0,0,0,0)
        
        lines_toolbar = QHBoxLayout()
        self.lbl_session_name = QLabel("Sélectionnez une session")
        self.lbl_session_name.setStyleSheet("font-weight: bold; font-size: 14px;")
        lines_toolbar.addWidget(self.lbl_session_name)
        lines_toolbar.addStretch()
        
        self.btn_validate = QPushButton("Valider & Ajuster Stock")
        self.btn_validate.setProperty("class", "primary")
        self.btn_validate.clicked.connect(self._validate_session)
        self.btn_validate.hide()
        lines_toolbar.addWidget(self.btn_validate)
        lines_layout.addLayout(lines_toolbar)

        self.lines_table = DataTable(["Ligne ID", "Matière", "Théorique", "Physique", "Écart", "Action"])
        self.lines_table.row_double_clicked.connect(self._edit_line)
        lines_layout.addWidget(self.lines_table)
        splitter.addWidget(lines_container)
        
        splitter.setSizes([300, 600])
        layout.addWidget(splitter)

    def refresh(self):
        session = get_session()
        try:
            svc = InventoryService(session)
            sessions = svc.get_sessions()
            rows = []
            for s in sessions:
                rows.append([s.id, s.name, format_date(s.session_date), s.status])
            self.sessions_table.set_data(rows)
            
            if self.current_session_id:
                self._load_lines(self.current_session_id)
            else:
                self.lines_table.set_data([])
        finally:
            session.close()

    def filter(self, text: str):
        self.sessions_table.filter_rows(text)

    def _new_session(self):
        name, ok = QInputDialog.getText(self, "Nouvel Inventaire", "Nom de la session:")
        if ok and name.strip():
            session = get_session()
            try:
                svc = InventoryService(session)
                sess = svc.start_session(name.strip())
                self.current_session_id = sess.id
                show_success(self, "Succès", "Session d'inventaire créée")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _on_session_selected(self, sess_id: int):
        self.current_session_id = sess_id
        self._load_lines(sess_id)

    def _load_lines(self, sess_id: int):
        session = get_session()
        try:
            svc = InventoryService(session)
            sess = svc.get_session(sess_id)
            if sess:
                self.lbl_session_name.setText(f"Session: {sess.name} ({sess.status})")
                rows = []
                for line in sess.lines:
                    rows.append([
                        line.id,
                        line.material.designation,
                        line.theoretical_qty,
                        line.physical_qty,
                        line.discrepancy,
                        "✏️ Éditer" if sess.status == "en_cours" else ""
                    ])
                self.lines_table.set_data(rows)
                self.btn_validate.setVisible(sess.status == "en_cours")
        finally:
            session.close()

    def _edit_line(self, line_id: int):
        if not self.btn_validate.isVisible():
            return # not en cours

        session = get_session()
        try:
            # Quick lookup to get current physical qty
            from app.models.inventory import InventoryLine
            line = session.get(InventoryLine, line_id)
            if line:
                dlg = AdjustLineDialog(self, line.material.designation, line.theoretical_qty, line.physical_qty)
                if dlg.exec() == QDialog.Accepted:
                    qty, reason = dlg.get_data()
                    svc = InventoryService(session)
                    svc.update_line(line_id, qty, reason)
                    self._load_lines(self.current_session_id)
        finally:
            session.close()

    def _validate_session(self):
        if not self.current_session_id: return
        
        if confirm_action(self, "Valider", "Êtes-vous sûr de vouloir valider ? Le stock physique des matières sera mis à jour définitivement."):
            session = get_session()
            try:
                svc = InventoryService(session)
                svc.complete_session(self.current_session_id)
                show_success(self, "Validé", "L'inventaire a été validé et le stock mis à jour.")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()


class AdjustLineDialog(QDialog):
    def __init__(self, parent, material_name, theoretical, physical):
        super().__init__(parent)
        self.setWindowTitle(f"Ajuster: {material_name}")
        
        layout = QFormLayout(self)
        
        layout.addRow("Stock théorique:", QLabel(str(theoretical)))
        
        self.qty = QDoubleSpinBox()
        self.qty.setRange(0, 999999)
        self.qty.setValue(physical)
        layout.addRow("Stock physique:", self.qty)
        
        self.reason = QLineEdit()
        layout.addRow("Raison (optionnel):", self.reason)
        
        btns = QHBoxLayout()
        bc = QPushButton("Annuler"); bc.clicked.connect(self.reject); btns.addWidget(bc)
        bs = QPushButton("Enregistrer"); bs.setProperty("class", "primary"); bs.clicked.connect(self.accept); btns.addWidget(bs)
        layout.addRow(btns)

    def get_data(self):
        return self.qty.value(), self.reason.text().strip() or None
