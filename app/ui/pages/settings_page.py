"""Settings page — manage application settings including printer configuration."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFormLayout, QLineEdit, QComboBox, QGroupBox, QScrollArea, QFrame
)
import win32print
from PySide6.QtCore import Qt
from datetime import date
from app.ui.components.confirm_dialog import show_error, show_success
from app.database.engine import get_session
from app.services.settings_service import SettingsService
from app.utils.formatters import format_date

class SettingsPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Paramètres")
        title.setStyleSheet("font-size: 24px; font-weight: bold;")
        layout.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.NoFrame)
        
        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setSpacing(24)

        # Company Info
        company_group = QGroupBox("Informations de l'entreprise")
        company_layout = QFormLayout(company_group)
        company_layout.setSpacing(12)
        
        self.company_name = QLineEdit()
        self.company_phone = QLineEdit()
        self.company_address = QLineEdit()
        self.receipt_footer = QLineEdit()
        
        company_layout.addRow("Nom:", self.company_name)
        company_layout.addRow("Téléphone:", self.company_phone)
        company_layout.addRow("Adresse:", self.company_address)
        company_layout.addRow("Pied de ticket:", self.receipt_footer)
        content_layout.addWidget(company_group)

        # Printer Settings
        printer_group = QGroupBox("Imprimante Windows")
        printer_layout = QFormLayout(printer_group)
        printer_layout.setSpacing(12)

        self.printer_type = QComboBox()
        self.printer_type.addItems([
            "thermique (ESC/POS Win32Raw)",
            "standard (A4/PDF Windows)"
        ])
        printer_layout.addRow("Type d'imprimante:", self.printer_type)

        printer_row = QHBoxLayout()
        self.printer_name = QComboBox()
        printer_row.addWidget(self.printer_name)
        
        btn_refresh_printers = QPushButton("🔄")
        btn_refresh_printers.setToolTip("Actualiser la liste des imprimantes")
        btn_refresh_printers.setFixedWidth(40)
        btn_refresh_printers.clicked.connect(self._populate_printers)
        printer_row.addWidget(btn_refresh_printers)
        
        printer_layout.addRow("Nom de l'imprimante:", printer_row)

        btns_test = QHBoxLayout()
        btn_test_int = QPushButton("Test Impression Interne")
        btn_test_int.clicked.connect(self._test_print_internal)
        btns_test.addWidget(btn_test_int)

        btn_test_cust = QPushButton("Test Impression Client")
        btn_test_cust.clicked.connect(self._test_print_customer)
        btns_test.addWidget(btn_test_cust)

        printer_layout.addRow("", btns_test)

        content_layout.addWidget(printer_group)

        # Database Backup
        backup_group = QGroupBox("Sauvegarde de la base de donnees")
        backup_layout = QVBoxLayout(backup_group)
        
        backup_btns = QHBoxLayout()
        btn_backup = QPushButton("Sauvegarder maintenant")
        btn_backup.setProperty("class", "primary")
        btn_backup.clicked.connect(self._create_backup)
        backup_btns.addWidget(btn_backup)
        
        btn_restore = QPushButton("Restaurer une sauvegarde...")
        btn_restore.clicked.connect(self._restore_backup)
        backup_btns.addWidget(btn_restore)
        backup_btns.addStretch()
        backup_layout.addLayout(backup_btns)
        
        self.backup_info = QLabel("")
        self.backup_info.setStyleSheet("font-size: 12px; padding: 6px;")
        backup_layout.addWidget(self.backup_info)
        
        content_layout.addWidget(backup_group)
        content_layout.addStretch()
        
        scroll.setWidget(content)
        layout.addWidget(scroll)

        # Save Action
        actions = QHBoxLayout()
        actions.addStretch()
        btn_save = QPushButton("Enregistrer les parametres")
        btn_save.setProperty("class", "primary")
        btn_save.setMinimumWidth(200)
        btn_save.clicked.connect(self._save_settings)
        actions.addWidget(btn_save)
        layout.addLayout(actions)

        self.refresh()

    def _populate_printers(self):
        self.printer_name.clear()
        printers = win32print.EnumPrinters(win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS)
        for printer in printers:
            self.printer_name.addItem(printer[2])

    def refresh(self):
        session = get_session()
        try:
            svc = SettingsService(session)
            self.company_name.setText(svc.get_company_name())
            self.company_phone.setText(svc.get_company_phone())
            self.company_address.setText(svc.get_company_address())
            self.receipt_footer.setText(svc.get_receipt_footer())
            
            p_type = svc.get("printer_type", "thermique")
            idx = 0 if p_type == "thermique" else 1
            self.printer_type.setCurrentIndex(idx)
            
            self._populate_printers()
            saved_printer = svc.get("printer_name", "")
            if not saved_printer:
                try:
                    saved_printer = win32print.GetDefaultPrinter()
                except Exception:
                    pass
            
            idx = self.printer_name.findText(saved_printer)
            if idx >= 0:
                self.printer_name.setCurrentIndex(idx)
            
            self._update_backup_info()
        finally:
            session.close()

    def _save_settings(self):
        session = get_session()
        try:
            svc = SettingsService(session)
            svc.set("company_name", self.company_name.text().strip())
            svc.set("company_phone", self.company_phone.text().strip())
            svc.set("company_address", self.company_address.text().strip())
            svc.set("receipt_footer", self.receipt_footer.text().strip())
            
            p_type = self.printer_type.currentText().split(" ")[0]
            svc.set("printer_type", p_type)
            svc.set("printer_name", self.printer_name.currentText())
            
            show_success(self, "Succès", "Paramètres enregistrés")
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _test_print_internal(self):
        self._save_settings()
        session = get_session()
        try:
            from app.printing.printer_manager import PrinterManager
            pm = PrinterManager(session)
            test_data = {
                "reference": "TEST-001",
                "customer": "Client Test",
                "date": format_date(date.today()),
                "items": [{"product_name": "Miroir Décoratif", "quantity": 1}],
                "estimated_cost": 5000.0,
            }
            svc = SettingsService(session)
            company = {"name": svc.get_company_name(), "phone": svc.get_company_phone()}
            path = pm.print_internal_ticket(test_data, company)
            if path:  # Only standard fallback might return a path
                import os; os.startfile(path)
            show_success(self, "Succès", "Ticket interne envoyé à l'imprimante.")
        except Exception as e:
            show_error(self, "Erreur Impression", str(e))
        finally:
            session.close()

    def _test_print_customer(self):
        self._save_settings()
        session = get_session()
        try:
            from app.printing.printer_manager import PrinterManager
            pm = PrinterManager(session)
            test_data = {
                "reference": "TEST-001",
                "customer": "Client Test",
                "date": format_date(date.today()),
                "items": [{"product_name": "Miroir Décoratif", "quantity": 1}],
                "estimated_cost": 5000.0,
            }
            svc = SettingsService(session)
            company = {
                "name": svc.get_company_name(), "phone": svc.get_company_phone(),
                "address": svc.get_company_address(), "footer": svc.get_receipt_footer(),
            }
            path = pm.print_customer_receipt(test_data, company)
            if path:
                import os; os.startfile(path)
            show_success(self, "Succès", "Ticket client envoyé à l'imprimante.")
        except Exception as e:
            show_error(self, "Erreur Impression", str(e))
        finally:
            session.close()

    def filter(self, text: str):
        pass

    def _create_backup(self):
        try:
            from app.utils.backup import create_backup
            path = create_backup()
            show_success(self, "Sauvegarde", f"Sauvegarde creee:\n{path}")
            self._update_backup_info()
        except Exception as e:
            show_error(self, "Erreur", str(e))

    def _restore_backup(self):
        from PySide6.QtWidgets import QFileDialog
        from app.ui.components.confirm_dialog import confirm_action
        path, _ = QFileDialog.getOpenFileName(self, "Choisir une sauvegarde", "", "Fichiers DB (*.db)")
        if path:
            if confirm_action(self, "Restaurer", "Etes-vous sur ? La base actuelle sera ecrasee par la sauvegarde. Redemarrage necessaire."):
                try:
                    from app.utils.backup import restore_backup
                    restore_backup(path)
                    show_success(self, "Restauration", "Base restauree. Veuillez redemarrer l'application.")
                except Exception as e:
                    show_error(self, "Erreur", str(e))

    def _update_backup_info(self):
        try:
            from app.utils.backup import list_backups
            backups = list_backups()
            if backups:
                latest = backups[0]
                self.backup_info.setText(
                    f"Derniere sauvegarde: {latest['date']}  ({latest['size_mb']} MB)  —  "
                    f"Total: {len(backups)} sauvegarde(s)"
                )
            else:
                self.backup_info.setText("Aucune sauvegarde trouvee.")
        except Exception:
            self.backup_info.setText("")
