"""Application-wide constants and enumerations."""
from enum import Enum


class OrderStatus(str, Enum):
    DRAFT = "brouillon"
    CONFIRMED = "confirmée"
    PENDING = "en_attente"
    IN_PRODUCTION = "en_production"
    CUTTING = "en_découpe"
    ASSEMBLY = "en_assemblage"
    FINISHING = "finition"
    READY = "prêt"
    DELIVERED = "livrée"
    CANCELLED = "annulée"

    @property
    def label(self) -> str:
        return ORDER_STATUS_LABELS.get(self, self.value)


class OrderUrgency(str, Enum):
    NORMAL = "normale"
    FAST = "rapide"
    URGENT = "urgente"

    @property
    def label(self) -> str:
        return URGENCY_LABELS.get(self, self.value)


class PaymentStatus(str, Enum):
    UNPAID = "non_payé"
    DEPOSIT = "acompte"
    PARTIAL = "payé_partiellement"
    PAID = "payé_totalement"

    @property
    def label(self) -> str:
        return PAYMENT_STATUS_LABELS.get(self, self.value)


class PaymentMethod(str, Enum):
    CASH = "espèces"
    CHECK = "chèque"
    TRANSFER = "virement"
    OTHER = "autre"


class StockMovementType(str, Enum):
    STOCK_IN = "entrée"
    STOCK_OUT = "sortie"
    RESERVATION = "réservation"
    RELEASE = "libération"
    ADJUSTMENT = "ajustement"
    POS_SALE = "vente_pos"
    INITIAL = "stock_initial"


class DebtStatus(str, Enum):
    TO_PAY = "à_payer"
    PARTIAL = "partiellement_payé"
    PAID = "payé"
    OVERDUE = "en_retard"

    @property
    def label(self) -> str:
        return DEBT_STATUS_LABELS.get(self, self.value)


class SaleStatus(str, Enum):
    COMPLETED = "terminée"
    CANCELLED = "annulée"
    REFUNDED = "remboursée"


class InventoryStatus(str, Enum):
    IN_PROGRESS = "en_cours"
    COMPLETED = "terminé"
    CANCELLED = "annulé"


class ItemCategory(str, Enum):
    MIRROR = "miroir"
    ARMOIRE = "armoire"
    OTHER = "autre"


class MaterialCategory(str, Enum):
    GLASS = "verre"
    WOOD = "bois"
    METAL = "métal"
    HARDWARE = "quincaillerie"
    PAINT = "peinture"
    ADHESIVE = "adhésif"
    PACKAGING = "emballage"
    OTHER = "autre"


class MaterialUnit(str, Enum):
    PIECE = "pièce"
    METER = "mètre"
    SQUARE_METER = "m²"
    KILOGRAM = "kg"
    LITER = "litre"
    ROLL = "rouleau"
    SHEET = "feuille"
    BOX = "boîte"


# Status labels for display
ORDER_STATUS_LABELS = {
    OrderStatus.DRAFT: "Brouillon",
    OrderStatus.CONFIRMED: "Confirmée",
    OrderStatus.PENDING: "En attente",
    OrderStatus.IN_PRODUCTION: "En production",
    OrderStatus.CUTTING: "En découpe",
    OrderStatus.ASSEMBLY: "En assemblage",
    OrderStatus.FINISHING: "Finition",
    OrderStatus.READY: "Prêt",
    OrderStatus.DELIVERED: "Livrée",
    OrderStatus.CANCELLED: "Annulée",
}

URGENCY_LABELS = {
    OrderUrgency.NORMAL: "Normale",
    OrderUrgency.FAST: "Rapide",
    OrderUrgency.URGENT: "Urgente",
}

PAYMENT_STATUS_LABELS = {
    PaymentStatus.UNPAID: "Non payé",
    PaymentStatus.DEPOSIT: "Acompte",
    PaymentStatus.PARTIAL: "Payé partiellement",
    PaymentStatus.PAID: "Payé totalement",
}

DEBT_STATUS_LABELS = {
    DebtStatus.TO_PAY: "À payer",
    DebtStatus.PARTIAL: "Partiellement payé",
    DebtStatus.PAID: "Payé",
    DebtStatus.OVERDUE: "En retard",
}

# Statuses where stock is reserved
RESERVED_STATUSES = {
    OrderStatus.CONFIRMED,
    OrderStatus.PENDING,
    OrderStatus.IN_PRODUCTION,
    OrderStatus.CUTTING,
    OrderStatus.ASSEMBLY,
    OrderStatus.FINISHING,
    OrderStatus.READY,
}

# Ordered production stages for progress tracking
PRODUCTION_STAGES = [
    OrderStatus.CONFIRMED,
    OrderStatus.PENDING,
    OrderStatus.IN_PRODUCTION,
    OrderStatus.CUTTING,
    OrderStatus.ASSEMBLY,
    OrderStatus.FINISHING,
    OrderStatus.READY,
    OrderStatus.DELIVERED,
]

# Sidebar navigation
SIDEBAR_ITEMS = [
    ("dashboard", "Tableau de bord", "dashboard"),
    ("pos", "POS", "pos"),
    ("orders", "Commandes", "orders"),
    ("clients", "Clients", "clients"),
    ("debts", "Créances Globales", "debts"),
    ("stock", "Stock", "stock"),
    ("inventory", "Inventaire", "inventory"),
    ("suppliers", "Fournisseurs & Dettes", "suppliers"),
    ("reports", "Rapports", "reports"),
    ("zakat", "Zakat", "zakat"),
    ("settings", "Paramètres", "settings"),
]
