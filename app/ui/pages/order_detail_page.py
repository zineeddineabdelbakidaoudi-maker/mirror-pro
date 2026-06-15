"""Order detail page with tabs for items, materials, payments, and status history."""
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QDialog,
    QFormLayout, QLineEdit, QComboBox, QDoubleSpinBox, QLabel,
    QTabWidget, QTextEdit, QFrame, QScrollArea, QSpinBox, QInputDialog
)
from datetime import date
from PySide6.QtCore import Qt, Signal
from app.ui.components.data_table import DataTable
from app.ui.components.status_badge import StatusBadge, STATUS_DISPLAY
from app.ui.components.confirm_dialog import confirm_action, show_error, show_success
from app.ui.theme import Theme
from app.database.engine import get_session
from app.services.order_service import OrderService
from app.services.stock_service import StockService
from app.utils.formatters import format_currency, format_date, format_quantity
from app.utils.constants import OrderStatus, RESERVED_STATUSES, PRODUCTION_STAGES


class OrderDetailPage(QWidget):
    back_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.order_id = None
        self._setup_ui()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        # Top bar
        top = QHBoxLayout()
        btn_back = QPushButton("← Retour aux commandes")
        btn_back.setProperty("class", "ghost")
        btn_back.setCursor(Qt.PointingHandCursor)
        btn_back.clicked.connect(self.back_requested.emit)
        top.addWidget(btn_back)
        top.addStretch()
        self.ref_label = QLabel()
        self.ref_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        top.addWidget(self.ref_label)
        top.addStretch()
        self.status_badge = StatusBadge("brouillon")
        top.addWidget(self.status_badge)
        self.urgency_badge = StatusBadge("normale")
        top.addWidget(self.urgency_badge)
        layout.addLayout(top)

        # Info bar
        info_bar = QHBoxLayout()
        self.customer_label = QLabel()
        info_bar.addWidget(self.customer_label)
        self.date_label = QLabel()
        info_bar.addWidget(self.date_label)
        self.cost_label = QLabel()
        self.cost_label.setStyleSheet("font-weight: 600;")
        info_bar.addWidget(self.cost_label)
        self.balance_label = QLabel()
        self.balance_label.setStyleSheet("font-weight: 600;")
        info_bar.addWidget(self.balance_label)
        self.notes_label = QLabel()
        self.notes_label.setStyleSheet(f"color: {Theme.instance().colors.text_secondary}; font-style: italic; margin-left: 10px;")
        info_bar.addWidget(self.notes_label)
        
        self.btn_edit_notes = QPushButton("✎")
        self.btn_edit_notes.setToolTip("Éditer les notes")
        self.btn_edit_notes.setProperty("class", "ghost")
        self.btn_edit_notes.setFixedSize(28, 28)
        self.btn_edit_notes.clicked.connect(self._edit_notes)
        info_bar.addWidget(self.btn_edit_notes)
        info_bar.addStretch()
        layout.addLayout(info_bar)

        # Action buttons
        actions = QHBoxLayout()
        self.btn_confirm = QPushButton("✓ Confirmer")
        self.btn_confirm.setProperty("class", "primary")
        self.btn_confirm.clicked.connect(self._confirm_order)
        actions.addWidget(self.btn_confirm)

        self.btn_status = QComboBox()
        self.btn_status.addItem("Changer statut...", "")
        for s in PRODUCTION_STAGES:
            self.btn_status.addItem(STATUS_DISPLAY.get(s.value, s.value), s.value)
        self.btn_status.currentIndexChanged.connect(self._change_status)
        actions.addWidget(self.btn_status)

        self.btn_complete = QPushButton("🏁 Terminer et livrer")
        self.btn_complete.setProperty("class", "success")
        self.btn_complete.clicked.connect(self._complete_order)
        actions.addWidget(self.btn_complete)

        self.btn_cancel = QPushButton("❌  Annuler commande")
        self.btn_cancel.setProperty("class", "danger")
        self.btn_cancel.clicked.connect(self._cancel_order)
        actions.addWidget(self.btn_cancel)

        self.btn_delete_order = QPushButton("🗑  Supprimer")
        self.btn_delete_order.setProperty("class", "danger")
        self.btn_delete_order.clicked.connect(self._delete_order)
        actions.addWidget(self.btn_delete_order)

        self.btn_print_internal = QPushButton("🖨 Ticket interne")
        self.btn_print_internal.clicked.connect(self._print_internal)
        actions.addWidget(self.btn_print_internal)

        self.btn_print_customer = QPushButton("🧾 Ticket client")
        self.btn_print_customer.clicked.connect(self._print_customer)
        actions.addWidget(self.btn_print_customer)

        actions.addStretch()
        layout.addLayout(actions)

        # Tabs
        self.tabs = QTabWidget()
        self.tab_items = QWidget()
        self.tab_payments = QWidget()
        self.tab_history = QWidget()
        self.tabs.addTab(self.tab_items, "Articles & Matières")
        self.tabs.addTab(self.tab_payments, "Paiements")
        self.tabs.addTab(self.tab_history, "Historique")
        layout.addWidget(self.tabs)

        self._setup_items_tab()
        self._setup_payments_tab()
        self._setup_history_tab()

    def _setup_items_tab(self):
        layout = QVBoxLayout(self.tab_items)
        layout.setSpacing(12)

        toolbar = QHBoxLayout()
        btn_add_mat_global = QPushButton("+ Matière")
        btn_add_mat_global.setProperty("class", "primary")
        btn_add_mat_global.clicked.connect(self._add_global_material)
        toolbar.addWidget(btn_add_mat_global)
        toolbar.addStretch()
        self.total_cost_label = QLabel()
        self.total_cost_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        toolbar.addWidget(self.total_cost_label)
        layout.addLayout(toolbar)

        self.items_container = QVBoxLayout()
        self.items_container.setSpacing(8)
        layout.addLayout(self.items_container)
        layout.addStretch()

    def _setup_payments_tab(self):
        layout = QVBoxLayout(self.tab_payments)
        toolbar = QHBoxLayout()
        btn_pay = QPushButton("+ Enregistrer paiement")
        btn_pay.setProperty("class", "primary")
        btn_pay.clicked.connect(self._add_payment)
        toolbar.addWidget(btn_pay)
        toolbar.addStretch()
        self.payment_summary = QLabel()
        toolbar.addWidget(self.payment_summary)
        layout.addLayout(toolbar)
        cols = ["ID", "Date", "Montant", "Mode", "Type", "Notes"]
        self.payments_table = DataTable(cols)
        layout.addWidget(self.payments_table)

    def _setup_history_tab(self):
        layout = QVBoxLayout(self.tab_history)
        cols = ["ID", "Date", "Ancien statut", "Nouveau statut", "Notes"]
        self.history_table = DataTable(cols)
        layout.addWidget(self.history_table)

    def load_order(self, order_id: int):
        self.order_id = order_id
        self.refresh()

    def refresh(self):
        if not self.order_id:
            return
        session = get_session()
        try:
            svc = OrderService(session)
            order = svc.get_order(self.order_id)
            if not order:
                return

            self.ref_label.setText(order.reference)
            self.status_badge.update_status(order.status)
            self.urgency_badge.update_status(order.urgency)
            self.customer_label.setText(f"👤 {order.customer_name}")
            self.date_label.setText(f"📅 {format_date(order.order_date)}")
            self.cost_label.setText(f"Coût estimé: {format_currency(order.estimated_cost)}")

            if order.final_selling_price:
                bal = order.remaining_balance
                self.balance_label.setText(f"Prix final: {format_currency(order.final_selling_price)} | Reste: {format_currency(bal)}")
            else:
                paid = order.total_payments
                if paid > 0:
                    self.balance_label.setText(f"Acompte payé: {format_currency(paid)}")
                else:
                    self.balance_label.setText("")

            if order.notes:
                self.notes_label.setText(f"Notes: {order.notes}")
            else:
                self.notes_label.setText("")

            # Button visibility
            is_draft = order.status == OrderStatus.DRAFT.value
            is_cancelled = order.status == OrderStatus.CANCELLED.value
            is_delivered = order.status == OrderStatus.DELIVERED.value
            self.btn_confirm.setVisible(is_draft)
            self.btn_status.setVisible(not is_draft and not is_cancelled and not is_delivered)
            self.btn_complete.setVisible(not is_draft and not is_cancelled and not is_delivered)
            self.btn_cancel.setVisible(not is_cancelled and not is_delivered)

            # Items tab
            while self.items_container.count():
                item = self.items_container.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()

            t = Theme.instance().colors
            total_mat_cost = 0.0
            for oi in order.items:
                item_frame = QFrame()
                item_frame.setStyleSheet(f"""
                    background-color: {t.bg_card};
                    border: 1px solid {t.border};
                    border-radius: 8px;
                """)
                item_layout = QVBoxLayout(item_frame)
                item_layout.setContentsMargins(14, 10, 14, 10)

                # Item header
                header = QHBoxLayout()
                name_lbl = QLabel(f"▸ {oi.product_name} (x{oi.quantity})")
                name_lbl.setStyleSheet("font-weight: 600; font-size: 14px;")
                header.addWidget(name_lbl)
                if oi.dimensions:
                    dim_lbl = QLabel(oi.dimensions)
                    dim_lbl.setStyleSheet(f"color: {t.text_secondary};")
                    header.addWidget(dim_lbl)
                if oi.category:
                    cat_badge = StatusBadge(oi.category if oi.category in STATUS_DISPLAY else "normale")
                    header.addWidget(cat_badge)
                header.addStretch()
                cost_lbl = QLabel(f"Matières: {format_currency(oi.material_cost)}")
                cost_lbl.setStyleSheet(f"color: {t.accent}; font-weight: 600;")
                header.addWidget(cost_lbl)

                btn_add_mat = QPushButton("+ Matière")
                btn_add_mat.setFixedHeight(30)
                btn_add_mat.clicked.connect(lambda _, iid=oi.id: self._add_material(iid))
                header.addWidget(btn_add_mat)

                btn_del_item = QPushButton("Supprimer")
                btn_del_item.setFixedHeight(30)
                btn_del_item.setStyleSheet(f"background-color: {t.danger}; color: white; border: none; border-radius: 6px; padding: 4px 12px;")
                btn_del_item.clicked.connect(lambda _, iid=oi.id: self._remove_item(iid))
                header.addWidget(btn_del_item)
                item_layout.addLayout(header)

                # Materials list
                for om in oi.materials:
                    mat_row = QHBoxLayout()
                    mat_name = om.material.designation if om.material else "?"
                    mat_row.addWidget(QLabel(f"    ◦ {mat_name}"))
                    mat_row.addWidget(QLabel(f"{om.required_quantity:.2f} {om.unit or ''}"))
                    mat_row.addWidget(QLabel(f"× {format_currency(om.unit_cost)}"))
                    line_lbl = QLabel(f"= {format_currency(om.line_cost)}")
                    line_lbl.setStyleSheet("font-weight: 500;")
                    mat_row.addWidget(line_lbl)
                    mat_row.addStretch()
                    btn_del_mat = QPushButton("Supprimer")
                    btn_del_mat.setFixedHeight(30)
                    btn_del_mat.setStyleSheet(f"background-color: {t.danger}; color: white; border: none; border-radius: 6px; padding: 4px 12px;")
                    btn_del_mat.clicked.connect(lambda _, mid=om.id: self._remove_material(mid))
                    mat_row.addWidget(btn_del_mat)
                    item_layout.addLayout(mat_row)

                total_mat_cost += oi.material_cost
                self.items_container.addWidget(item_frame)

            self.total_cost_label.setText(
                f"Total matières: {format_currency(total_mat_cost)} | "
                f"Main d'œuvre: {format_currency(order.labor_cost)} | "
                f"Coût estimé: {format_currency(order.estimated_cost)}"
            )

            # Payments tab
            payments = svc.get_payments(self.order_id)
            rows = []
            total_paid = 0
            for p in payments:
                rows.append([p.id, format_date(p.payment_date, True),
                             format_currency(p.amount), p.payment_method,
                             p.payment_type, p.notes or ""])
                total_paid += p.amount
            self.payments_table.set_data(rows)
            self.payment_summary.setText(
                f"Total payé: {format_currency(total_paid)} | "
                f"Prix final: {format_currency(order.final_selling_price)} | "
                f"Reste: {format_currency(order.remaining_balance)}"
            )

            # History tab
            history = svc.get_status_history(self.order_id)
            h_rows = []
            for h in history:
                h_rows.append([h.id, format_date(h.created_at, True),
                               STATUS_DISPLAY.get(h.old_status, h.old_status or "—"),
                               STATUS_DISPLAY.get(h.new_status, h.new_status),
                               h.notes or ""])
            self.history_table.set_data(h_rows)
        finally:
            session.close()

    def _add_global_material(self):
        dlg = AddMaterialDialog(self)
        if dlg.exec() == QDialog.Accepted:
            mat_id, qty, cost, unit = dlg.get_data()
            session = get_session()
            try:
                svc = OrderService(session)
                order = svc.get_order(self.order_id)
                # Ensure there is an item to attach the material to
                if not order.items:
                    item = svc.add_order_item(
                        self.order_id,
                        product_name="Article Personnalisé",
                        quantity=1,
                        category="sur_mesure",
                        selling_price=0.0
                    )
                    item_id = item.id
                else:
                    item_id = order.items[0].id
                
                svc.add_order_material(item_id, mat_id, qty, cost, unit)
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _add_item(self):
        dlg = AddItemDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            session = get_session()
            try:
                svc = OrderService(session)
                svc.add_order_item(self.order_id, **data)
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _remove_item(self, item_id: int):
        if not confirm_action(self, "Supprimer", "Supprimer cet article et ses matières ?"):
            return
        session = get_session()
        try:
            svc = OrderService(session)
            svc.remove_order_item(item_id)
            self.refresh()
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _add_material(self, order_item_id: int):
        dlg = AddMaterialDialog(self)
        if dlg.exec() == QDialog.Accepted:
            mat_id, qty, cost, unit = dlg.get_data()
            session = get_session()
            try:
                svc = OrderService(session)
                svc.add_order_material(order_item_id, mat_id, qty, cost, unit)
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _remove_material(self, om_id: int):
        if not confirm_action(self, "Retirer", "Retirer cette matière de la commande ?"):
            return
        session = get_session()
        try:
            svc = OrderService(session)
            svc.remove_order_material(om_id)
            self.refresh()
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _confirm_order(self):
        if not confirm_action(self, "Confirmer",
                              "Confirmer la commande ?\nLe stock sera réservé automatiquement."):
            return
        session = get_session()
        try:
            svc = OrderService(session)
            svc.confirm_order(self.order_id)
            show_success(self, "Confirmée", "Commande confirmée et stock réservé")
            self.refresh()
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _change_status(self, index):
        if index <= 0:
            return
        new_status = self.btn_status.currentData()
        if not new_status:
            return
        session = get_session()
        try:
            svc = OrderService(session)
            svc.update_status(self.order_id, new_status)
            self.refresh()
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()
        self.btn_status.setCurrentIndex(0)

    def _cancel_order(self):
        if not confirm_action(self, "Annuler",
                              "Annuler cette commande ?\nLe stock réservé sera libéré."):
            return
        session = get_session()
        try:
            svc = OrderService(session)
            svc.cancel_order(self.order_id)
            show_success(self, "Annulée", "Commande annulée et stock libéré")
            self.refresh()
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _delete_order(self):
        if not confirm_action(self, "Supprimer",
                              "Voulez-vous vraiment supprimer définitivement cette commande ?\nCette action est irréversible."):
            return
        session = get_session()
        try:
            svc = OrderService(session)
            svc.delete_order(self.order_id)
            show_success(self, "Supprimée", "Commande supprimée avec succès")
            self.back_requested.emit()
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _complete_order(self):
        session = get_session()
        try:
            svc = OrderService(session)
            order = svc.get_order(self.order_id)
            dlg = CompleteOrderDialog(self, order=order)
            if dlg.exec() == QDialog.Accepted:
                name, price = dlg.get_data()
                svc.complete_order(self.order_id, name, price)
                show_success(self, "Livrée", "Commande terminée avec succès")
                self.refresh()
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _edit_notes(self):
        if not self.order_id: return
        session = get_session()
        try:
            svc = OrderService(session)
            order = svc.get_order(self.order_id)
            if order:
                text, ok = QInputDialog.getText(
                    self, "Éditer Notes", "Notes:", 
                    QLineEdit.EchoMode.Normal, order.notes or ""
                )
                if ok:
                    svc.update_order_info(self.order_id, notes=text.strip() or None)
                    self.refresh()
        except Exception as e:
            show_error(self, "Erreur", str(e))
        finally:
            session.close()

    def _add_payment(self):
        dlg = PaymentDialog(self)
        if dlg.exec() == QDialog.Accepted:
            amount, method, ptype, notes = dlg.get_data()
            session = get_session()
            try:
                svc = OrderService(session)
                svc.add_payment(self.order_id, amount, method, ptype, notes)
                show_success(self, "Paiement", "Paiement enregistré")
                self.refresh()
            except Exception as e:
                show_error(self, "Erreur", str(e))
            finally:
                session.close()

    def _print_internal(self):
        session = get_session()
        try:
            from app.services.settings_service import SettingsService
            from app.printing.printer_manager import PrinterManager
            svc = OrderService(session)
            ss = SettingsService(session)
            pm = PrinterManager(session)
            
            data = svc.get_order_cost_summary(self.order_id)
            # Ensure date string for ticket
            data['date'] = format_date(date.today())
            
            company = {"name": ss.get_company_name(), "phone": ss.get_company_phone()}
            
            path = pm.print_internal_ticket(data, company)
            if path:
                import os; os.startfile(path)
            else:
                show_success(self, "Impression", "Ticket interne imprimé avec succès")
        except Exception as e:
            show_error(self, "Impression", str(e))
        finally:
            session.close()

    def _print_customer(self):
        session = get_session()
        try:
            from app.services.settings_service import SettingsService
            from app.printing.printer_manager import PrinterManager
            svc = OrderService(session)
            ss = SettingsService(session)
            pm = PrinterManager(session)
            
            data = svc.get_order_cost_summary(self.order_id)
            data['date'] = format_date(date.today())
            
            company = {
                "name": ss.get_company_name(), "phone": ss.get_company_phone(),
                "address": ss.get_company_address(), "footer": ss.get_receipt_footer(),
            }
            
            path = pm.print_customer_receipt(data, company)
            if path:
                import os; os.startfile(path)
            else:
                show_success(self, "Impression", "Ticket client imprimé avec succès")
        except Exception as e:
            show_error(self, "Impression", str(e))
        finally:
            session.close()


class AddItemDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter un article")
        self.setMinimumWidth(420)
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        
        self.product_combo = QComboBox()
        self.products = []
        session = get_session()
        try:
            from app.services.catalog_service import CatalogService
            svc = CatalogService(session)
            self.products = [p for p in svc.get_all_products() if p.product_type != "finished_product"]
            for p in self.products:
                self.product_combo.addItem(p.name, p.id)
        finally:
            session.close()
        
        layout.addRow("Produit *:", self.product_combo)
        
        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(0.01, 999999.0)
        self.qty_spin.setValue(1)
        self.qty_spin.setDecimals(2)
        layout.addRow("Quantité:", self.qty_spin)
        
        self.dim_input = QLineEdit()
        self.dim_input.setPlaceholderText("ex: 120x80cm (optionnel)")
        layout.addRow("Dimensions:", self.dim_input)
        
        btns = QHBoxLayout()
        bc = QPushButton("Annuler"); bc.clicked.connect(self.reject); btns.addWidget(bc)
        bs = QPushButton("Ajouter"); bs.setProperty("class", "primary")
        bs.clicked.connect(self.accept); btns.addWidget(bs)
        layout.addRow(btns)

    def get_data(self):
        prod_name = self.product_combo.currentText()
        cat = "autre"
        price = 0.0
        idx = self.product_combo.currentIndex()
        if 0 <= idx < len(self.products):
            p = self.products[idx]
            cat = p.category
            price = p.selling_price
            
        return {
            "product_name": prod_name,
            "quantity": self.qty_spin.value(),
            "dimensions": self.dim_input.text().strip() or None,
            "category": cat,
            "selling_price": price,
            "notes": None,
        }


class AddMaterialDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Ajouter une matière")
        self.setMinimumWidth(480)
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        self.mat_combo = QComboBox()
        self.materials = []
        session = get_session()
        try:
            svc = StockService(session)
            self.materials = svc.get_all_materials()
            for m in self.materials:
                avail = m.quantity_available
                self.mat_combo.addItem(
                    f"{m.designation} ({avail:.1f} {m.unit} dispo)", m.id)
        finally:
            session.close()
        self.mat_combo.currentIndexChanged.connect(self._on_mat_change)
        layout.addRow("Matière *:", self.mat_combo)

        # Unit selector — populated when material chosen
        self.unit_combo = QComboBox()
        layout.addRow("Unité de facturation:", self.unit_combo)
        self.unit_combo.currentIndexChanged.connect(self._on_unit_change)

        hint = QLabel("💡 L'unité détermine le prix de vente appliqué")
        hint.setStyleSheet("color: #888; font-size: 11px;")
        layout.addRow("", hint)

        self.qty_spin = QDoubleSpinBox()
        self.qty_spin.setRange(0.01, 999999)
        self.qty_spin.setValue(1)
        layout.addRow("Quantité:", self.qty_spin)

        self.cost_spin = QDoubleSpinBox()
        self.cost_spin.setRange(0, 9999999)
        self.cost_spin.setSuffix(" DA")
        layout.addRow("Prix unitaire (vente):", self.cost_spin)

        self.line_cost_label = QLabel("= 0 DA")
        self.line_cost_label.setStyleSheet("font-weight: bold; font-size: 14px; color: #EAB308;")
        layout.addRow("Total ligne:", self.line_cost_label)

        self.qty_spin.valueChanged.connect(self._update_line_cost)
        self.cost_spin.valueChanged.connect(self._update_line_cost)

        if self.materials:
            self._on_mat_change(0)

        btns = QHBoxLayout()
        bc = QPushButton("Annuler"); bc.clicked.connect(self.reject); btns.addWidget(bc)
        bs = QPushButton("Ajouter"); bs.setProperty("class", "primary")
        bs.clicked.connect(self.accept); btns.addWidget(bs)
        layout.addRow(btns)

    def _on_mat_change(self, idx):
        if 0 <= idx < len(self.materials):
            m = self.materials[idx]
            self.unit_combo.blockSignals(True)
            self.unit_combo.clear()
            self.unit_combo.addItem(
                f"{m.unit} (principal) — {format_currency(m.selling_price or 0)}/u",
                (m.unit, m.selling_price or 0)
            )
            if m.secondary_unit and m.secondary_selling_price:
                self.unit_combo.addItem(
                    f"{m.secondary_unit} (détail) — {format_currency(m.secondary_selling_price)}/u",
                    (m.secondary_unit, m.secondary_selling_price)
                )
            self.unit_combo.blockSignals(False)
            self._on_unit_change(0)

    def _on_unit_change(self, idx):
        data = self.unit_combo.currentData()
        if data:
            _, price = data
            self.cost_spin.setValue(price)
        self._update_line_cost()

    def _update_line_cost(self):
        lc = self.qty_spin.value() * self.cost_spin.value()
        self.line_cost_label.setText(f"= {format_currency(lc)}")

    def get_data(self):
        data = self.unit_combo.currentData()
        unit = data[0] if data else ""
        return (self.mat_combo.currentData(), self.qty_spin.value(),
                self.cost_spin.value(), unit)


class CompleteOrderDialog(QDialog):
    def __init__(self, parent=None, order=None):
        super().__init__(parent)
        self.order = order
        self.setWindowTitle("Terminer la commande")
        self.setMinimumWidth(440)
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        title = QLabel("Finaliser et livrer la commande")
        title.setStyleSheet("font-size: 15px; font-weight: bold;")
        layout.addRow(title)

        # Show estimated cost as reference
        if order:
            ref_label = QLabel(f"Coût estimé: {format_currency(order.estimated_cost)}")
            ref_label.setStyleSheet("color: #888; font-size: 12px;")
            layout.addRow(ref_label)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Nom du produit final")
        layout.addRow("Produit final *:", self.name_input)

        self.price_spin = QDoubleSpinBox()
        self.price_spin.setRange(0, 99999999)
        self.price_spin.setSuffix(" DA")
        # Pre-fill with estimated cost
        if order:
            self.price_spin.setValue(order.estimated_cost)
        layout.addRow("Prix de vente *:", self.price_spin)

        self.debt_warning = QLabel()
        self.debt_warning.setStyleSheet(
            "background: #450a0a; color: #fca5a5; border: 1px solid #ef4444;"
            "border-radius: 6px; padding: 8px; font-size: 12px;"
        )
        self.debt_warning.setWordWrap(True)
        self.debt_warning.hide()
        layout.addRow(self.debt_warning)

        # Show already paid
        if order:
            paid = order.total_payments
            self.paid_label = QLabel(f"Déjà payé: {format_currency(paid)}")
            self.paid_label.setStyleSheet("color: #22c55e; font-weight: 600;")
            layout.addRow(self.paid_label)

            self.remaining_label = QLabel()
            self.remaining_label.setStyleSheet("color: #ef4444; font-weight: bold; font-size: 13px;")
            layout.addRow(self.remaining_label)
            self.price_spin.valueChanged.connect(self._update_remaining)
            self._update_remaining()

        btns = QHBoxLayout()
        bc = QPushButton("Annuler"); bc.clicked.connect(self.reject); btns.addWidget(bc)
        bs = QPushButton("Terminer & Livrer"); bs.setProperty("class", "success")
        bs.clicked.connect(self._validate); btns.addWidget(bs)
        layout.addRow(btns)

    def _update_remaining(self):
        if not self.order:
            return
        price = self.price_spin.value()
        paid = self.order.total_payments
        remaining = max(0, price - paid)
        if remaining > 0:
            self.remaining_label.setText(f"⚠ Reste à payer: {format_currency(remaining)}")
            self.debt_warning.setText(
                f"⚠️  Ce client aura une créance de {format_currency(remaining)} DA.\n"
                f"Il sera marqué en rouge dans la liste des clients."
            )
            self.debt_warning.show()
        else:
            self.remaining_label.setText("✓ Commande soldée")
            self.remaining_label.setStyleSheet("color: #22c55e; font-weight: bold;")
            self.debt_warning.hide()

    def _validate(self):
        if not self.name_input.text().strip():
            show_error(self, "Validation", "Le nom est obligatoire"); return
        if self.price_spin.value() <= 0:
            show_error(self, "Validation", "Le prix doit être > 0"); return
        self.accept()

    def get_data(self):
        return self.name_input.text().strip(), self.price_spin.value()


class PaymentDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Enregistrer un paiement")
        self.setMinimumWidth(400)
        layout = QFormLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)
        self.amount_spin = QDoubleSpinBox()
        self.amount_spin.setRange(0.01, 99999999)
        self.amount_spin.setSuffix(" DA")
        layout.addRow("Montant *:", self.amount_spin)
        self.method_combo = QComboBox()
        self.method_combo.addItems(["espèces", "chèque", "virement", "autre"])
        layout.addRow("Mode:", self.method_combo)
        self.type_combo = QComboBox()
        self.type_combo.addItems(["versement", "acompte", "solde"])
        layout.addRow("Type:", self.type_combo)
        self.notes_input = QLineEdit()
        layout.addRow("Notes:", self.notes_input)
        btns = QHBoxLayout()
        bc = QPushButton("Annuler"); bc.clicked.connect(self.reject); btns.addWidget(bc)
        bs = QPushButton("Enregistrer"); bs.setProperty("class", "primary")
        bs.clicked.connect(self.accept); btns.addWidget(bs)
        layout.addRow(btns)

    def get_data(self):
        return (self.amount_spin.value(), self.method_combo.currentText(),
                self.type_combo.currentText(), self.notes_input.text().strip() or None)
