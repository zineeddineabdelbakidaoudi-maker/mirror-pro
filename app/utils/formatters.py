"""Formatting utilities for currency, dates, and numbers."""
from datetime import datetime, date
from typing import Optional


def format_currency(amount: Optional[float], currency: str = "DA") -> str:
    """Format amount as Algerian Dinar string."""
    if amount is None:
        return "—"
    if amount == int(amount):
        return f"{int(amount):,} {currency}".replace(",", " ")
    return f"{amount:,.2f} {currency}".replace(",", " ")


def format_date(d: Optional[date], include_time: bool = False) -> str:
    """Format date in French style DD/MM/YYYY."""
    if d is None:
        return "—"
    if include_time and isinstance(d, datetime):
        return d.strftime("%d/%m/%Y %H:%M")
    if isinstance(d, datetime):
        d = d.date()
    return d.strftime("%d/%m/%Y")


def format_quantity(qty: Optional[float], unit: str = "") -> str:
    """Format quantity with unit."""
    if qty is None:
        return "—"
    if qty == int(qty):
        result = str(int(qty))
    else:
        result = f"{qty:.2f}"
    if unit:
        result += f" {unit}"
    return result


def format_phone(phone: Optional[str]) -> str:
    """Format phone number for display."""
    if not phone:
        return "—"
    return phone.strip()


def generate_reference(prefix: str, count: int, d: Optional[date] = None) -> str:
    """Generate a reference number like CMD-00001."""
    return f"{prefix}-{count:05d}"


def truncate(text: str, max_len: int = 40) -> str:
    """Truncate text with ellipsis if too long."""
    if not text or len(text) <= max_len:
        return text or ""
    return text[:max_len - 1] + "…"
