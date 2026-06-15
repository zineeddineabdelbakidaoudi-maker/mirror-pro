"""Stock management page — full CRUD for materials with stock movements."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog,
    QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QLabel,
    QTabWidget, QTextEdit, QFrame, QMessageBox,
)
from PySide6.QtCore import Qt, Signal
from app.ui.components.data_table import DataTable
from app.ui.components.status_badge import StatusBadge
from app.ui.components.empty_state import EmptyState
from app.ui.components.confirm_dialog import confirm_action, show_error, show_success
from app.ui.theme import Theme
from app.database.engine import get_session
from app.services.stock_service import StockService
from app.utils.formatters import format_currency, format_quantity, format_date
from app.utils.constants import MaterialCategory, MaterialUnit


class StockPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.tabs = QTabWidget()
        self.tab_materials = QWidget()
        self.tab_products = QWidget()
        self.tabs.addTab(self.tab_materials, "Matières premières")
        self.tabs.addTab(self.tab_products, "Catalogue & POS")
        layout.addWidget(self.tabs)

        self._setup_materials_tab()
        self._setup_products_tab()

    def _setup_materials_tab(self):
        layout = QVBoxLayout(self.tab_materials)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Toolbar
        toolbar = QHBoxLayout()
        btn_add = QPushButton("+ Nouvelle matière")
        btn_add.setProperty("class", "primary")
        btn_add.clicked.connect(self._show_add_dialog)
        toolbar.addWidget(btn_add)

        btn_stock_in = QPushButton("📥 Entrée stock")
        btn_stock_in.clicked.connect(self._show_stock_in)
        toolbar.addWidget(btn_stock_in)

        btn_stock_out = QPushButton("📤 Sortie stock")
        btn_stock_out.clicked.connect(self._show_stock_out)
        toolbar.addWidget(btn_stock_out)

        btn_delete = QPushButton("🗑 Supprimer matière")
        btn_delete.setProperty("class", "danger")
        btn_delete.clicked.connect(self._delete_material)
        toolbar.addWidget(btn_delete)

        toolbar.addStretch()

        self.value_label = QLabel()
        self.value_label.setStyleSheet("font-size: 13px; font-weight: 500;")
        toolbar.addWidget(self.value_label)

        layout.addLayout(toolbar)

        # Table
        columns = ["ID", "Code", "Désignation", "Catégorie", "Unité", "Qté Détail",
                    "En stock", "Réservé", "Disponible", "Seuil min", "Coût Achat", "Prix Vente", "Valeur"]
        self.table = DataTable(columns)
        self.table.row_double_clicked.connect(self._on_double_click)
        layout.addWidget(self.table)

    def _setup_products_tab(self):
        layout = QVBoxLayout(self.tab_products)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        toolbar = QHBoxLayout()
        btn_add = QPushButton("+ Nouveau produit")
        btn_add.setProperty("class", "primary")
        btn_add.clicked.connect(self._show_add_product)
        toolbar.addWidget(btn_add)
        
        btn_delete = QPushButton("🗑 Supprimer produit")
        btn_delete.setProperty("class", "danger")
        btn_delete.clicked.connect(self._delete_product)
        toolbar.addWidget(btn_delete)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)

        columns = ["ID", "Nom", "Type", "POS", "Suivi Stock", "En stock", "Unité", "Prix Vente"]
        self.products_table = DataTable(columns)
        self.products_table.row_double_clicked.connect(self._on_edit_product)
        layout.addWidget(self.products_table)

    def refresh(self):
        session = get_session()
        try:
            svc = StockService(session)
            materials = svc.get_all_materials()
            rows = []
            for m in materials:
                def fmt_q(qty):
                    if not m.secondary_unit or not m.secondary_unit_qty or m.secondary_unit_qty <= 0:
                        return format_quantity(qty)
                    full_p = int(qty)
                    frac = qty - full_p
                    sec = round(frac * m.secondary_unit_qty, 2)
                    res = []
                    if full_p > 0:
                        res.append(f"{full_p} {m.unit}")
                    if sec > 0:
                        res.append(f"{sec:g} {m.secondary_unit}")
                    if not res:
                        return f"0 {m.unit}"
                    return " et ".join(res)
                    
                qte_detail = ""
                if m.secondary_unit and m.secondary_unit_qty and m.secondary_unit_qty > 0:
                    total_sec = round(m.quantity_on_hand * m.secondary_unit_qty, 2)
                    qte_detail = f"{total_sec:g} {m.secondary_unit}"
                    
                rows.append([
                    m.id, m.code or "", m.designation,
                    m.category, m.unit, qte_detail,
                    fmt_q(m.quantity_on_hand),
                    fmt_q(m.quantity_reserved),
                    fmt_q(m.quantity_available),
                    format_quantity(m.minimum_threshold),
                    format_currency(m.purchase_cost),
                    format_currency(m.selling_price),
                    format_currency(m.stock_value),
                ])
            self.table.set_data(rows)
            total_val = svc.get_stock_value()
            self.value_label.setText(f"Valeur totale: {format_currency(total_val)}")

            # Refresh Products
            from app.services.catalog_service import CatalogService
            cat_svc = CatalogService(session)
            products = cat_svc.get_all_products()
            p_rows = []
            for p in products:
                pos_str = "Oui" if p.sellable_in_pos else "Non"
                track_str = "Oui" if p.stock_tracked else "Non"
                p_rows.append([
                    p.id, p.name, p.product_type, pos_str, track_str,
                    format_quantity(p.quantity_on_hand), p.unit,
                    format_currency(p.selling_price)
                ])
            self.products_table.set_data(p_rows)

        finally:
            session.close()

    def filter(self, text: str):
        self.table.filter_rows(text)
        self.products_table.filter_rows(text)

    def _show_add_dialog(self):
        dlg = MaterialDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = get_session()
            try:
                svc = StockService(session)
                svc.create_material(**data)
                show_success(self, "Succès", "Matière ajoutée avec succès")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _on_double_click(self, material_id: int):
        dlg = MaterialDialog(self, material_id=material_id)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = get_session()
            try:
                svc = StockService(session)
                svc.update_material(material_id, **data)
                show_success(self, "Succès", "Matière modifiée avec succès")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _show_stock_in(self):
        material_id = self.table.get_selected_id()
        if not material_id:
            show_error(self, "Sélection", "Veuillez sélectionner une matière")
            return
        dlg = StockMovementDialog(self, material_id, is_in=True)
        if dlg.exec() == QDialog.Accepted:
            qty, reason = dlg.get_data()
            session = get_session()
            try:
                svc = StockService(session)
                svc.stock_in(material_id, qty, reason)
                show_success(self, "Succès", f"Entrée de {qty} enregistrée")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _show_stock_out(self):
        material_id = self.table.get_selected_id()
        if not material_id:
            show_error(self, "Sélection", "Veuillez sélectionner une matière")
            return
        dlg = StockMovementDialog(self, material_id, is_in=False)
        if dlg.exec() == QDialog.Accepted:
            qty, reason = dlg.get_data()
            session = get_session()
            try:
                svc = StockService(session)
                svc.stock_out(material_id, qty, reason)
                show_success(self, "Succès", f"Sortie de {qty} enregistrée")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _show_add_product(self):
        dlg = ProductDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = get_session()
            try:
                from app.services.catalog_service import CatalogService
                svc = CatalogService(session)
                svc.create_product(**data)
                show_success(self, "Succès", "Produit ajouté au catalogue")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _on_edit_product(self, product_id: int):
        dlg = ProductDialog(self, product_id=product_id)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = get_session()
            try:
                from app.services.catalog_service import CatalogService
                svc = CatalogService(session)
                svc.update_product(product_id, **data)
                show_success(self, "Succès", "Produit modifié avec succès")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _delete_material(self):
        material_id = self.table.get_selected_id()
        if not material_id:
            show_error(self, "Sélection", "Veuillez sélectionner une matière à supprimer")
            return
        if not confirm_action(self, "Supprimer", "Voulez-vous vraiment supprimer cette matière ?"):
            return
        session = get_session()
        try:
            svc = StockService(session)
            svc.delete_material(material_id)
            show_success(self, "Succès", "Matière supprimée avec succès")
            self.refresh()
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _delete_product(self):
        product_id = self.products_table.get_selected_id()
        if not product_id:
            show_error(self, "Sélection", "Veuillez sélectionner un produit à supprimer")
            return
        if not confirm_action(self, "Supprimer", "Voulez-vous vraiment supprimer ce produit ?"):
            return
        session = get_session()
        try:
            from app.services.catalog_service import CatalogService
            svc = CatalogService(session)
            svc.delete_product(product_id)
            show_success(self, "Succès", "Produit supprimé avec succès")
            self.refresh()
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()


class MaterialDialog(QDialog):
    """Dialog for adding/editing a material."""
    def __init__(self, parent=None, material_id: int = None):
        super().__init__(parent)
        self.material_id = material_id
        self.setWindowTitle("Modifier matière" if material_id else "Nouvelle matière")
        self.setMinimumWidth(450)
        self._setup_ui()
        if material_id:
            self._load_data()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("Généré automatiquement")
        self.code_input.setEnabled(False)
        layout.addRow("Code:", self.code_input)

        self.designation_input = QLineEdit()
        self.designation_input.setPlaceholderText("Nom de la matière")
        layout.addRow("Désignation *:", self.designation_input)

        self.category_combo = QComboBox()
        for cat in MaterialCategory:
            self.category_combo.addItem(cat.value, cat.value)
        layout.addRow("Catégorie:", self.category_combo)

        self.unit_combo = QComboBox()
        for u in MaterialUnit:
            self.unit_combo.addItem(u.value, u.value)
        layout.addRow("Unité:", self.unit_combo)

        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(0, 999999)
        self.qty_spin.setDecimals(2)
        layout.addRow("Quantité en stock:", self.qty_spin)

        self.threshold_spin = QDoubleSpinBox()
        self.threshold_spin.setRange(0, 99999)
        self.threshold_spin.setValue(5)
        layout.addRow("Seuil minimum:", self.threshold_spin)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 9999999)
        self.cost_spin.setDecimals(2)
        self.cost_spin.setSuffix(" DA")
        layout.addRow("Coût d'achat:", self.cost_spin)

        self.sell_spin = QDoubleSpinBox()
        self.sell_spin.setRange(0, 9999999)
        self.sell_spin.setDecimals(2)
        self.sell_spin.setSuffix(" DA")
        layout.addRow("Prix de vente:", self.sell_spin)

        # ── Section Vente Détail (unité secondaire) ──────────────
        sep_lbl = QLabel("── Vente détail (optionnel) ──")
        sep_lbl.setStyleSheet("color: #888; font-size: 12px; margin-top: 8px;")
        layout.addRow(sep_lbl)

        hint2 = QLabel("Ex: 1 feuille contient 6 mètres. Prix au mètre = X DA")
        hint2.setStyleSheet("color: #666; font-size: 11px;")
        layout.addRow(hint2)

        self.secondary_unit_combo = QComboBox()
        self.secondary_unit_combo.addItem("Aucune", None)
        for u in MaterialUnit:
            self.secondary_unit_combo.addItem(u.value, u.value)
        layout.addRow("Unité secondaire:", self.secondary_unit_combo)

        self.secondary_qty_spin = QDoubleSpinBox()
        self.secondary_qty_spin.setRange(0, 9999)
        self.secondary_qty_spin.setDecimals(2)
        self.secondary_qty_spin.setValue(0)
        self.secondary_qty_spin.setToolTip("Combien d'unités secondaires dans 1 unité principale")
        layout.addRow("Qte / unité principale:", self.secondary_qty_spin)

        self.secondary_sell_spin = QDoubleSpinBox()
        self.secondary_sell_spin.setRange(0, 9999999)
        self.secondary_sell_spin.setDecimals(2)
        self.secondary_sell_spin.setSuffix(" DA")
        layout.addRow("Prix vente / unité sec.:", self.secondary_sell_spin)

        self.location_input = QLineEdit()
        self.location_input.setPlaceholderText("Emplacement de stockage")
        layout.addRow("Emplacement:", self.location_input)

        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(80)
        layout.addRow("Notes:", self.notes_input)

        # Buttons
        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        btn_save = QPushButton("Enregistrer")
        btn_save.setProperty("class", "primary")
        btn_save.clicked.connect(self._validate_and_accept)
        btn_layout.addWidget(btn_save)
        layout.addRow(btn_layout)

    def _load_data(self):
        session = get_session()
        try:
            svc = StockService(session)
            m = svc.get_material(self.material_id)
            if m:
                self.code_input.setText(m.code or "")
                self.designation_input.setText(m.designation)
                idx = self.category_combo.findData(m.category)
                if idx >= 0:
                    self.category_combo.setCurrentIndex(idx)
                idx = self.unit_combo.findData(m.unit)
                if idx >= 0:
                    self.unit_combo.setCurrentIndex(idx)
                self.qty_spin.setValue(m.quantity_on_hand)
                self.threshold_spin.setValue(m.minimum_threshold)
                self.cost_spin.setValue(m.purchase_cost)
                self.sell_spin.setValue(m.selling_price)
                # Secondary unit
                if m.secondary_unit:
                    idx = self.secondary_unit_combo.findData(m.secondary_unit)
                    if idx >= 0:
                        self.secondary_unit_combo.setCurrentIndex(idx)
                self.secondary_qty_spin.setValue(m.secondary_unit_qty or 0)
                self.secondary_sell_spin.setValue(m.secondary_selling_price or 0)
                self.location_input.setText(m.storage_location or "")
                self.notes_input.setPlainText(m.notes or "")
        finally:
            session.close()

    def _validate_and_accept(self):
        if not self.designation_input.text().strip():
            show_error(self, "Validation", "La désignation est obligatoire")
            return
        self.accept()

    def get_data(self) -> dict:
        data = {
            "code": self.code_input.text().strip() or None,
            "designation": self.designation_input.text().strip(),
            "category": self.category_combo.currentData(),
            "unit": self.unit_combo.currentData(),
            "minimum_threshold": self.threshold_spin.value(),
            "purchase_cost": self.cost_spin.value(),
            "selling_price": self.sell_spin.value(),
            "secondary_unit": self.secondary_unit_combo.currentData(),
            "secondary_unit_qty": self.secondary_qty_spin.value() or None,
            "secondary_selling_price": self.secondary_sell_spin.value() or None,
            "storage_location": self.location_input.text().strip() or None,
            "notes": self.notes_input.toPlainText().strip() or None,
            "quantity_on_hand": self.qty_spin.value()
        }
        return data


class StockMovementDialog(QDialog):
    """Dialog for stock in/out operations."""
    def __init__(self, parent, material_id: int, is_in: bool = True):
        super().__init__(parent)
        self.material_id = material_id
        self.is_in = is_in
        self.setWindowTitle("Entrée stock" if is_in else "Sortie stock")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        # Show material info
        session = get_session()
        try:
            svc = StockService(session)
            m = svc.get_material(self.material_id)
            if m:
                info = QLabel(f"{m.designation} — En stock: {m.quantity_on_hand:.1f} {m.unit}")
                info.setStyleSheet("font-weight: 600; font-size: 14px;")
                layout.addRow(info)
        finally:
            session.close()

        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(0.01, 999999)
        self.qty_spin.setDecimals(2)
        self.qty_spin.setValue(1)
        layout.addRow("Quantité:", self.qty_spin)

        self.reason_input = QLineEdit()
        self.reason_input.setPlaceholderText("Raison du mouvement")
        layout.addRow("Raison:", self.reason_input)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Annuler")
        btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(btn_cancel)
        label = "Ajouter" if self.is_in else "Retirer"
        btn_save = QPushButton(label)
        btn_save.setProperty("class", "primary" if self.is_in else "danger")
        btn_save.clicked.connect(self.accept)
        btn_layout.addWidget(btn_save)
        layout.addRow(btn_layout)

    def get_data(self):
        return self.qty_spin.value(), self.reason_input.text().strip()


from PySide6.QtWidgets import QCheckBox

class ProductDialog(QDialog):
    """Dialog for creating/editing a product."""
    def __init__(self, parent=None, product_id: int = None):
        super().__init__(parent)
        self.product_id = product_id
        self.setWindowTitle("Modifier produit" if product_id else "Nouveau produit")
        self.setMinimumWidth(450)
        self._setup_ui()
        if product_id:
            self._load_data()

    def _setup_ui(self):
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.name_input = QLineEdit()
        layout.addRow("Nom *:", self.name_input)

        self.type_combo = QComboBox()
        self.type_combo.addItems(["finished_product", "raw_material", "service"])
        layout.addRow("Type:", self.type_combo)

        self.sellable_cb = QCheckBox("Disponible dans POS (Vente directe)")
        self.sellable_cb.setChecked(True)
        layout.addRow("", self.sellable_cb)

        self.stock_tracked_cb = QCheckBox("Suivre le stock")
        self.stock_tracked_cb.setChecked(True)
        layout.addRow("", self.stock_tracked_cb)

        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(0, 999999)
        layout.addRow("Quantité en stock:", self.qty_spin)

        self.min_stock_spin = QDoubleSpinBox()
        self.min_stock_spin.setRange(0, 99999)
        layout.addRow("Stock minimum:", self.min_stock_spin)

        self.unit_input = QLineEdit("pièce")
        layout.addRow("Unité:", self.unit_input)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 9999999)
        self.price_spin.setSuffix(" DA")
        layout.addRow("Prix de vente:", self.price_spin)

        btns = QHBoxLayout()
        bc = QPushButton("Annuler"); bc.clicked.connect(self.reject); btns.addWidget(bc)
        bs = QPushButton("Enregistrer"); bs.setProperty("class", "primary")
        bs.clicked.connect(self.accept); btns.addWidget(bs)
        layout.addRow(btns)

    def _load_data(self):
        session = get_session()
        try:
            from app.services.catalog_service import CatalogService
            svc = CatalogService(session)
            p = svc.get_product(self.product_id)
            if p:
                self.name_input.setText(p.name)
                self.type_combo.setCurrentText(p.product_type)
                self.sellable_cb.setChecked(p.sellable_in_pos)
                self.stock_tracked_cb.setChecked(p.stock_tracked)
                self.qty_spin.setValue(p.quantity_on_hand)
                self.min_stock_spin.setValue(p.minimum_stock or 0)
                self.unit_input.setText(p.unit)
                self.price_spin.setValue(p.selling_price)
        finally:
            session.close()

    def get_data(self):
        data = {
            "name": self.name_input.text().strip(),
            "product_type": self.type_combo.currentText(),
            "sellable_in_pos": self.sellable_cb.isChecked(),
            "stock_tracked": self.stock_tracked_cb.isChecked(),
            "minimum_stock": self.min_stock_spin.value(),
            "unit": self.unit_input.text().strip(),
            "selling_price": self.price_spin.value(),
            "quantity_on_hand": self.qty_spin.value()
        }
        return data
