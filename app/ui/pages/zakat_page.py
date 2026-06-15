"""Zakat page — calculate and record annual Zakat."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QDoubleSpinBox, QTextEdit, QFrame, QScrollArea, QGroupBox, QFormLayout,
)
from PySide6.QtCore import Qt
from app.database.engine import get_session
from app.services.zakat_service import ZakatService
from app.ui.components.data_table import DataTable
from app.ui.components.confirm_dialog import show_error, show_success
from app.ui.theme import Theme
from app.utils.formatters import format_currency


class ZakatPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._last_calc = None
        self._setup_ui()

    def _setup_ui(self):
        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)

        title = QLabel("Calcul de la Zakat")
        title.setProperty("class", "page_title")
        layout.addWidget(title)

        # --- Input section ---
        input_group = QGroupBox("Paramètres")
        input_form = QFormLayout(input_group)

        self.cash_spin = QDoubleSpinBox()
        self.cash_spin.setRange(0, 999_999_999)
        self.cash_spin.setSuffix(" DA")
        self.cash_spin.setDecimals(2)
        input_form.addRow("Trésorerie (Caisse + Banque):", self.cash_spin)

        self.receivables_spin = QDoubleSpinBox()
        self.receivables_spin.setRange(0, 999_999_999)
        self.receivables_spin.setSuffix(" DA")
        self.receivables_spin.setDecimals(2)
        input_form.addRow("Créances supplémentaires:", self.receivables_spin)

        self.nisab_spin = QDoubleSpinBox()
        self.nisab_spin.setRange(0, 999_999_999)
        self.nisab_spin.setSuffix(" DA")
        self.nisab_spin.setDecimals(2)
        self.nisab_spin.setValue(ZakatService.DEFAULT_NISAB_DZD)
        input_form.addRow("Nisab (seuil):", self.nisab_spin)

        layout.addWidget(input_group)

        btn_calc = QPushButton("Calculer la Zakat")
        btn_calc.setProperty("class", "primary")
        btn_calc.clicked.connect(self._calculate)
        layout.addWidget(btn_calc)

        # --- Results section ---
        results_group = QGroupBox("Résultat")
        results_layout = QVBoxLayout(results_group)
        t = Theme.instance().colors

        self.results_grid = QFormLayout()
        self.lbl_stock = QLabel("--")
        self.results_grid.addRow("Valeur du stock:", self.lbl_stock)
        self.lbl_receivables = QLabel("--")
        self.results_grid.addRow("Créances recouvrables:", self.lbl_receivables)
        self.lbl_debts = QLabel("--")
        self.results_grid.addRow("Dettes fournisseurs (déductibles):", self.lbl_debts)
        self.lbl_eligible = QLabel("--")
        self.lbl_eligible.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.results_grid.addRow("Assiette imposable:", self.lbl_eligible)

        self.lbl_zakat = QLabel("--")
        self.lbl_zakat.setStyleSheet(f"font-weight: bold; font-size: 20px; color: {t.success};")
        self.results_grid.addRow("Zakat due (2.5%):", self.lbl_zakat)

        results_layout.addLayout(self.results_grid)
        layout.addWidget(results_group)

        # Save
        save_row = QHBoxLayout()
        self.notes_input = QTextEdit()
        self.notes_input.setPlaceholderText("Notes optionnelles pour cet enregistrement...")
        self.notes_input.setMaximumHeight(80)
        save_row.addWidget(self.notes_input)

        btn_save = QPushButton("Enregistrer le Snapshot")
        btn_save.clicked.connect(self._save_snapshot)
        save_row.addWidget(btn_save)
        layout.addLayout(save_row)

        # --- History ---
        history_label = QLabel("Historique des Snapshots")
        history_label.setProperty("class", "section_title")
        layout.addWidget(history_label)

        self.history_table = DataTable(["ID", "Année", "Trésorerie", "Stock", "Créances", "Dettes", "Zakat Due"])
        layout.addWidget(self.history_table)

        layout.addStretch()
        scroll.setWidget(container)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)

    def refresh(self):
        self._load_history()

    def filter(self, text: str):
        self.history_table.filter_rows(text)

    def _calculate(self):
        session = get_session()
        try:
            svc = ZakatService(session)
            result = svc.calculate(
                cash_assets=self.cash_spin.value(),
                extra_receivables=self.receivables_spin.value(),
                nisab=self.nisab_spin.value()
            )
            self._last_calc = result

            self.lbl_stock.setText(format_currency(result["stock_valuation"]))
            self.lbl_receivables.setText(format_currency(result["receivables"]))
            self.lbl_debts.setText(format_currency(result["payable_debts"]))
            self.lbl_eligible.setText(format_currency(result["eligible_assets"]))
            self.lbl_zakat.setText(format_currency(result["zakat_due"]))
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _save_snapshot(self):
        if not self._last_calc:
            show_error(self, "Erreur", "Veuillez d'abord calculer la Zakat.")
            return

        session = get_session()
        try:
            svc = ZakatService(session)
            svc.save_snapshot(self._last_calc, self.notes_input.toPlainText().strip() or None)
            show_success(self, "Enregistré", "Le snapshot Zakat a été sauvegardé.")
            self._load_history()
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _load_history(self):
        session = get_session()
        try:
            svc = ZakatService(session)
            snaps = svc.get_snapshots()
            rows = []
            for s in snaps:
                rows.append([
                    s.id, s.year,
                    format_currency(s.cash_assets),
                    format_currency(s.stock_valuation),
                    format_currency(s.receivables),
                    format_currency(s.payable_debts),
                    format_currency(s.zakat_due),
                ])
            self.history_table.set_data(rows)
        finally:
            session.close()
