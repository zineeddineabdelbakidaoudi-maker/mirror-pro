"""Reports page — export data to CSV/PDF."""
from datetime import date
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QDateEdit, QComboBox, QFileDialog
)
from PySide6.QtCore import Qt, QDate
from app.database.engine import get_session
from app.reports.report_engine import ReportEngine
from app.reports.csv_exporter import CsvExporter
from app.reports.pdf_exporter import PdfExporter
from app.ui.components.data_table import DataTable
from app.ui.components.confirm_dialog import show_error, show_success
import os

class ReportsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(20)
        
        title = QLabel("Rapports & Exports")
        title.setProperty("class", "page_title")
        layout.addWidget(title)
        
        # Report selector
        filters_layout = QHBoxLayout()
        
        self.report_type = QComboBox()
        self.report_type.addItems([
            "Commandes & Bénéfices",
            "Ventes POS",
            "Dettes Fournisseurs (En cours)"
        ])
        filters_layout.addWidget(QLabel("Type de rapport:"))
        filters_layout.addWidget(self.report_type)
        
        # Dates
        self.date_from = QDateEdit(QDate.currentDate().addDays(-30))
        self.date_from.setCalendarPopup(True)
        filters_layout.addWidget(QLabel("Du:"))
        filters_layout.addWidget(self.date_from)
        
        self.date_to = QDateEdit(QDate.currentDate())
        self.date_to.setCalendarPopup(True)
        filters_layout.addWidget(QLabel("Au:"))
        filters_layout.addWidget(self.date_to)
        
        filters_layout.addStretch()
        layout.addLayout(filters_layout)
        
        # Action Buttons
        actions_layout = QHBoxLayout()
        
        btn_generate = QPushButton("Générer l'aperçu")
        btn_generate.clicked.connect(self._preview_report)
        actions_layout.addWidget(btn_generate)

        btn_csv = QPushButton("Exporter en CSV")
        btn_csv.setProperty("class", "primary")
        btn_csv.clicked.connect(self._export_csv)
        actions_layout.addWidget(btn_csv)
        
        btn_pdf = QPushButton("Exporter en PDF (A4)")
        btn_pdf.setProperty("class", "primary")
        btn_pdf.clicked.connect(self._export_pdf)
        actions_layout.addWidget(btn_pdf)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Preview table
        self.preview_table = DataTable([])
        layout.addWidget(self.preview_table)
        
    def _preview_report(self):
        data, _, _ = self._get_report_data_and_name("csv")
        if not data:
            self.preview_table.set_data([])
            return
            
        if isinstance(data, list) and len(data) > 0:
            columns = list(data[0].keys())
            self.preview_table.setup_columns(columns)
            
            rows = []
            for row_dict in data:
                rows.append([str(v) for v in row_dict.values()])
            self.preview_table.set_data(rows)
        else:
            self.preview_table.set_data([])

    def refresh(self):
        pass

    def filter(self, text: str):
        pass

    def _get_report_data_and_name(self, ext="csv"):
        rpt_type = self.report_type.currentIndex()
        d_from = self.date_from.date()
        d_to = self.date_to.date()
        
        start_date = date(d_from.year(), d_from.month(), d_from.day())
        end_date = date(d_to.year(), d_to.month(), d_to.day())
        
        session = get_session()
        data = []
        filename = ""
        title = ""
        try:
            engine = ReportEngine(session)
            
            if rpt_type == 0:
                data = engine.get_orders_report(start_date, end_date)
                filename = f"creances et benefices.{ext}"
                title = f"Rapport des Commandes & Bénéfices ({start_date} au {end_date})"
            elif rpt_type == 1:
                data = engine.get_sales_report(start_date, end_date)
                filename = f"rapport_ventes_pos_{start_date}_au_{end_date}.{ext}"
                title = f"Rapport des Ventes POS ({start_date} au {end_date})"
            else:
                data = engine.get_debts_report()
                filename = f"rapport_dettes_fournisseurs_{date.today()}.{ext}"
                title = f"Rapport des Dettes Fournisseurs ({date.today()})"
                
        finally:
            session.close()
            
        return data, filename, title

    def _export_csv(self):
        data, filename, _ = self._get_report_data_and_name("csv")
        if not data:
            show_error(self, "Export", "Aucune donnée trouvée pour cette période.")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder CSV", filename, "Fichiers CSV (*.csv)")
        if path:
            if CsvExporter.export(data, path):
                show_success(self, "Succès", "Export CSV réussi")
            else:
                show_error(self, "Erreur", "L'export a échoué. Vérifiez que le fichier n'est pas ouvert.")

    def _export_pdf(self):
        data, filename, title = self._get_report_data_and_name("pdf")
        if not data:
            show_error(self, "Export", "Aucune donnée trouvée pour cette période.")
            return
            
        path, _ = QFileDialog.getSaveFileName(self, "Sauvegarder PDF", filename, "Fichiers PDF (*.pdf)")
        if path:
            if PdfExporter.export(data, path, title):
                show_success(self, "Succès", "Export PDF réussi")
                os.startfile(path)
            else:
                show_error(self, "Erreur", "L'export PDF a échoué.")
