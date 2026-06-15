"""Status badge component with color coding."""
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import Qt
from app.ui.theme import Theme

STATUS_COLORS = {
    # Order statuses
    "brouillon": ("text_secondary", "bg_tertiary"),
    "confirmée": ("info", "info_bg"),
    "en_attente": ("warning", "warning_bg"),
    "en_production": ("accent", "accent_bg"),
    "en_découpe": ("accent", "accent_bg"),
    "en_assemblage": ("accent", "accent_bg"),
    "finition": ("accent", "accent_bg"),
    "prêt": ("success", "success_bg"),
    "livrée": ("success", "success_bg"),
    "annulée": ("danger", "danger_bg"),
    # Payment statuses
    "non_payé": ("danger", "danger_bg"),
    "acompte": ("warning", "warning_bg"),
    "payé_partiellement": ("warning", "warning_bg"),
    "payé_totalement": ("success", "success_bg"),
    # Urgency
    "normale": ("text_secondary", "bg_tertiary"),
    "rapide": ("warning", "warning_bg"),
    "urgente": ("danger", "danger_bg"),
    # Debt
    "à_payer": ("warning", "warning_bg"),
    "partiellement_payé": ("warning", "warning_bg"),
    "payé": ("success", "success_bg"),
    "en_retard": ("danger", "danger_bg"),
}

STATUS_DISPLAY = {
    "brouillon": "Brouillon",
    "confirmée": "Confirmée",
    "en_attente": "En attente",
    "en_production": "En production",
    "en_découpe": "En découpe",
    "en_assemblage": "En assemblage",
    "finition": "Finition",
    "prêt": "Prêt",
    "livrée": "Livrée",
    "annulée": "Annulée",
    "non_payé": "Non payé",
    "acompte": "Acompte",
    "payé_partiellement": "Partiel",
    "payé_totalement": "Payé",
    "normale": "Normale",
    "rapide": "Rapide",
    "urgente": "Urgente",
    "à_payer": "À payer",
    "partiellement_payé": "Partiel",
    "payé": "Payé",
    "en_retard": "En retard",
}


class StatusBadge(QLabel):
    def __init__(self, status: str, parent=None):
        super().__init__(parent)
        self.update_status(status)

    def update_status(self, status: str):
        t = Theme.instance().colors
        display = STATUS_DISPLAY.get(status, status)
        fg_attr, bg_attr = STATUS_COLORS.get(status, ("text_secondary", "bg_tertiary"))
        fg = getattr(t, fg_attr, t.text_secondary)
        bg = getattr(t, bg_attr, t.bg_tertiary)

        self.setText(f" {display} ")
        self.setAlignment(Qt.AlignCenter)
        self.setStyleSheet(f"""
            background-color: {bg};
            color: {fg};
            border-radius: 4px;
            padding: 3px 10px;
            font-size: 11px;
            font-weight: 600;
        """)
