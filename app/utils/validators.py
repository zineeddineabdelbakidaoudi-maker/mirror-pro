"""Input validation utilities."""
from typing import Optional, Tuple


def validate_required(value: Optional[str], field_name: str) -> Tuple[bool, str]:
    """Validate that a field is not empty."""
    if not value or not value.strip():
        return False, f"{field_name} est obligatoire"
    return True, ""


def validate_positive_number(value, field_name: str) -> Tuple[bool, str]:
    """Validate that value is a positive number."""
    try:
        num = float(value)
        if num < 0:
            return False, f"{field_name} doit être positif"
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name} doit être un nombre valide"


def validate_positive_nonzero(value, field_name: str) -> Tuple[bool, str]:
    """Validate that value is a strictly positive number."""
    try:
        num = float(value)
        if num <= 0:
            return False, f"{field_name} doit être supérieur à 0"
        return True, ""
    except (ValueError, TypeError):
        return False, f"{field_name} doit être un nombre valide"


def validate_phone(phone: Optional[str]) -> Tuple[bool, str]:
    """Basic phone number validation."""
    if not phone or not phone.strip():
        return True, ""  # Phone is optional
    cleaned = phone.strip().replace(" ", "").replace("-", "")
    if not cleaned.replace("+", "").isdigit():
        return False, "Numéro de téléphone invalide"
    if len(cleaned) < 8:
        return False, "Numéro trop court"
    return True, ""


def validate_stock_availability(
    available: float, requested: float, material_name: str
) -> Tuple[bool, str]:
    """Check if enough stock is available."""
    if requested > available:
        return (
            False,
            f"Stock insuffisant pour {material_name}: "
            f"disponible {available:.2f}, demandé {requested:.2f}",
        )
    return True, ""
