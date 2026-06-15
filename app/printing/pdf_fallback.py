"""PDF fallback for receipt preview when no printer is available."""
import os
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import mm
from reportlab.lib.units import mm as mm_unit
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.utils import ImageReader
from app.config import DATA_DIR, APP_DIR


RECEIPT_DIR = DATA_DIR / "receipts"
RECEIPT_DIR.mkdir(exist_ok=True)

# Logo path — relative to app assets
LOGO_PATH = APP_DIR / "app" / "assets" / "logo.png"


def _create_canvas(filename: str, width_mm: int = 80):
    """Create a receipt-sized PDF canvas."""
    filepath = RECEIPT_DIR / filename
    width = width_mm * mm_unit
    height = 400 * mm_unit  # Will be trimmed
    c = canvas.Canvas(str(filepath), pagesize=(width, height))
    c.setFont("Helvetica", 9)
    return c, filepath, width


def _draw_logo(c, y: float, width: float, max_height: float = 30) -> float:
    """Draw the company logo centered. Returns new y position after logo."""
    if LOGO_PATH.exists():
        try:
            img = ImageReader(str(LOGO_PATH))
            iw, ih = img.getSize()
            scale = min(max_height * mm_unit / ih, (width * 0.6) / iw)
            draw_w = iw * scale
            draw_h = ih * scale
            x = (width - draw_w) / 2
            c.drawImage(str(LOGO_PATH), x, y - draw_h, draw_w, draw_h, preserveAspectRatio=True, mask='auto')
            return y - draw_h - 6
        except Exception:
            pass
    return y


def _draw_centered(c, text: str, y: float, width: float, font_size: int = 9, bold: bool = False):
    font = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(font, font_size)
    text_width = c.stringWidth(text, font, font_size)
    c.drawString((width - text_width) / 2, y, text)


def _draw_separator(c, y: float, width: float):
    c.setFont("Helvetica", 8)
    _draw_centered(c, "─" * 40, y, width, 8)


def generate_internal_ticket_pdf(order_data: dict, company_info: dict) -> str:
    """Generate internal cost ticket PDF. Returns file path."""
    filename = f"ticket_interne_{order_data.get('reference', 'X')}_{datetime.now().strftime('%H%M%S')}.pdf"
    c, filepath, width = _create_canvas(filename)
    margin = 5 * mm_unit
    y = 385 * mm_unit

    # Header — Logo first
    y = _draw_logo(c, y, width, max_height=22)
    _draw_centered(c, "═══ TICKET INTERNE ═══", y, width, 11, True)
    y -= 15
    _draw_centered(c, company_info.get("name", "Atelier Glass Charaf"), y, width, 10, True)
    y -= 12
    _draw_centered(c, f"Tél: {company_info.get('phone', '')}", y, width, 8)
    y -= 15
    _draw_separator(c, y, width)
    y -= 12

    # Order info
    c.setFont("Helvetica-Bold", 9)
    c.drawString(margin, y, f"Commande: {order_data.get('reference', '')}")
    y -= 12
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, f"Date: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
    y -= 12
    c.drawString(margin, y, f"Client: {order_data.get('customer', '')}")
    y -= 12
    urgency = order_data.get('urgency', 'normale')
    if urgency != 'normale':
        c.setFont("Helvetica-Bold", 10)
        c.drawString(margin, y, f"*** {urgency.upper()} ***")
        y -= 12
    y -= 5
    _draw_separator(c, y, width)
    y -= 15

    # Items and materials
    for item in order_data.get("items", []):
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, y, f"► {item['product_name']} (x{item['quantity']})")
        y -= 12

        for mat in item.get("materials", []):
            c.setFont("Helvetica", 8)
            name = mat["material_name"][:20]
            qty_str = f"{mat['quantity']:.1f} {mat.get('unit', '')}"
            cost_str = f"{mat['line_cost']:,.0f} DA"
            c.drawString(margin + 5, y, f"  {name}")
            c.drawString(margin + 120, y, qty_str)
            c.drawRightString(width - margin, y, cost_str)
            y -= 11

        c.setFont("Helvetica-Bold", 8)
        c.drawString(margin + 5, y, f"  Sous-total matières:")
        c.drawRightString(width - margin, y, f"{item['material_cost']:,.0f} DA")
        y -= 14

    _draw_separator(c, y, width)
    y -= 14

    notes = order_data.get('notes')
    if notes:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, y, "NOTES:")
        y -= 12
        c.setFont("Helvetica", 9)
        # Handle multiline notes naively or simply draw them
        for line in notes.split('\n'):
            c.drawString(margin, y, line)
            y -= 12
        y -= 2

    # Totals
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, "Total matières:")
    val_mat = order_data.get('total_material_cost') or 0
    c.drawRightString(width - margin, y, f"{val_mat:,.0f} DA")
    y -= 12
    c.drawString(margin, y, "Main d'œuvre:")
    val_labor = order_data.get('labor_cost') or 0
    c.drawRightString(width - margin, y, f"{val_labor:,.0f} DA")
    y -= 12
    c.drawString(margin, y, "Autres charges:")
    val_other = order_data.get('other_charges') or 0
    c.drawRightString(width - margin, y, f"{val_other:,.0f} DA")
    y -= 14
    _draw_separator(c, y, width)
    y -= 14
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "COÛT ESTIMÉ:")
    val_est = order_data.get('estimated_cost') or 0
    c.drawRightString(width - margin, y, f"{val_est:,.0f} DA")

    c.save()
    return str(filepath)


def generate_customer_receipt_pdf(order_data: dict, company_info: dict) -> str:
    """Generate customer receipt PDF. No internal costs. Returns file path."""
    filename = f"recu_client_{order_data.get('reference', 'X')}_{datetime.now().strftime('%H%M%S')}.pdf"
    c, filepath, width = _create_canvas(filename)
    margin = 5 * mm_unit
    y = 385 * mm_unit

    # Header — Logo first
    y = _draw_logo(c, y, width, max_height=22)
    _draw_centered(c, company_info.get("name", "Atelier Glass Charaf"), y, width, 12, True)
    y -= 14
    _draw_centered(c, f"Tél: {company_info.get('phone', '')}", y, width, 9)
    y -= 12
    _draw_centered(c, company_info.get("address", ""), y, width, 8)
    y -= 15
    _draw_separator(c, y, width)
    y -= 14

    # Order info
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, f"Réf: {order_data.get('reference', '')}")
    y -= 12
    c.drawString(margin, y, f"Date: {datetime.now().strftime('%d/%m/%Y')}")
    y -= 12
    c.drawString(margin, y, f"Client: {order_data.get('customer', '')}")
    y -= 15
    _draw_separator(c, y, width)
    y -= 14

    # Product
    product = order_data.get("final_product_name", "Produit")
    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, product)
    y -= 15

    # Price
    price = order_data.get("final_selling_price") or 0
    c.setFont("Helvetica-Bold", 11)
    c.drawString(margin, y, "Prix total:")
    c.drawRightString(width - margin, y, f"{price:,.0f} DA")
    y -= 14
    _draw_separator(c, y, width)
    y -= 14

    notes = order_data.get('notes')
    if notes:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, y, "NOTES:")
        y -= 12
        c.setFont("Helvetica", 9)
        for line in notes.split('\n'):
            c.drawString(margin, y, line)
            y -= 12
        y -= 2

    # Payments
    total_paid = order_data.get("total_payments") or 0
    remaining = order_data.get("remaining_balance") or 0
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, "Montant payé:")
    c.drawRightString(width - margin, y, f"{total_paid:,.0f} DA")
    y -= 12
    if remaining > 0:
        c.setFont("Helvetica-Bold", 9)
        c.drawString(margin, y, "Reste à payer:")
        c.drawRightString(width - margin, y, f"{remaining:,.0f} DA")
        y -= 12

    y -= 10
    _draw_separator(c, y, width)
    y -= 14

    # Footer
    footer = company_info.get("footer", "Merci pour votre confiance !")
    _draw_centered(c, footer, y, width, 9)

    c.save()
    return str(filepath)


def generate_payment_receipt_pdf(payment_data: dict, company_info: dict) -> str:
    """Generate payment receipt PDF."""
    filename = f"recu_paiement_{payment_data.get('order_ref', 'X')}_{datetime.now().strftime('%H%M%S')}.pdf"
    c, filepath, width = _create_canvas(filename)
    margin = 5 * mm_unit
    y = 385 * mm_unit

    y = _draw_logo(c, y, width, max_height=20)
    _draw_centered(c, company_info.get("name", "Atelier Glass Charaf"), y, width, 12, True)
    y -= 14
    _draw_centered(c, f"Tél: {company_info.get('phone', '')}", y, width, 9)
    y -= 15
    _draw_centered(c, "─── REÇU DE PAIEMENT ───", y, width, 10, True)
    y -= 15

    c.setFont("Helvetica", 9)
    c.drawString(margin, y, f"Réf commande: {payment_data.get('order_ref', '')}")
    y -= 12
    c.drawString(margin, y, f"Client: {payment_data.get('customer', '')}")
    y -= 12
    c.drawString(margin, y, f"Date: {payment_data.get('date', '')}")
    y -= 14
    _draw_separator(c, y, width)
    y -= 14

    c.setFont("Helvetica-Bold", 10)
    c.drawString(margin, y, "Montant reçu:")
    amt = payment_data.get('amount') or 0
    c.drawRightString(width - margin, y, f"{amt:,.0f} DA")
    y -= 12
    c.setFont("Helvetica", 9)
    c.drawString(margin, y, f"Mode: {payment_data.get('method', 'espèces')}")
    y -= 14

    rem = payment_data.get('remaining') or 0
    if rem > 0:
        c.drawString(margin, y, "Reste à payer:")
        c.drawRightString(width - margin, y, f"{rem:,.0f} DA")
        y -= 14

    _draw_separator(c, y, width)
    y -= 14
    footer = company_info.get("footer", "Merci !")
    _draw_centered(c, footer, y, width, 9)

    c.save()
    return str(filepath)
