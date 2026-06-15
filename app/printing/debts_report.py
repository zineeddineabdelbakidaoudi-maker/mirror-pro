"""PDF Report generator for debts (créances)."""
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from app.config import DATA_DIR, APP_DIR, get_logo_path
from app.utils.formatters import format_currency

REPORTS_DIR = DATA_DIR / "reports"
REPORTS_DIR.mkdir(exist_ok=True)
LOGO_PATH = get_logo_path()

def generate_debts_report(debts_data: list, total_debt: float) -> str:
    """
    Generate an A4 PDF report of all debts.
    debts_data is a list of dicts: {"client": "Name", "phone": "Phone", "count": int, "total": float}
    Returns the absolute path to the generated PDF.
    """
    filename = "creance.pdf"
    filepath = REPORTS_DIR / filename
    
    # Simple deduplication if file exists
    counter = 1
    while filepath.exists():
        try:
            # Check if we can overwrite it (is it locked by PDF viewer?)
            with open(filepath, 'a'): pass
            break
        except IOError:
            filename = f"creance_{counter}.pdf"
            filepath = REPORTS_DIR / filename
            counter += 1
    
    doc = SimpleDocTemplate(
        str(filepath),
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Title style
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=15,
        alignment=1, # Center
        textColor=colors.HexColor('#2563eb'), # Modern blue
        fontName="Helvetica-Bold"
    )
    
    subtitle_style = ParagraphStyle(
        'SubTitleStyle',
        parent=styles['Normal'],
        fontSize=12,
        spaceAfter=25,
        alignment=1,
        textColor=colors.HexColor('#64748b')
    )
    
    # Header with logo
    header_data = []
    if LOGO_PATH.exists():
        try:
            img_reader = ImageReader(str(LOGO_PATH))
            orig_w, orig_h = img_reader.getSize()
            aspect = orig_w / float(orig_h)
            desired_h = 2.5 * cm
            desired_w = desired_h * aspect
            img = Image(str(LOGO_PATH), width=desired_w, height=desired_h)
            header_data = [[img, Paragraph("<b>Atelier Glass Charaf</b><br/>Gestion Professionnelle", styles["Normal"])]]
        except Exception:
            header_data = [[Paragraph("<b>Atelier Glass Charaf</b>", styles["Heading2"])]]
    else:
        header_data = [[Paragraph("<b>Atelier Glass Charaf</b>", styles["Heading2"])]]
        
    if header_data:
        t_header = Table(header_data, colWidths=[3*cm, 13*cm])
        t_header.setStyle(TableStyle([
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ]))
        elements.append(t_header)
        elements.append(Spacer(1, 0.5*cm))
            
    elements.append(Paragraph("Rapport Global des Créances", title_style))
    elements.append(Paragraph(f"Édité le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", subtitle_style))
    elements.append(Spacer(1, 0.5*cm))
    
    # Table data
    data = [["Client", "Téléphone", "Nb Commandes", "Total Créance"]]
    
    for row in debts_data:
        data.append([
            row["client"],
            row["phone"] or "-",
            str(row["count"]),
            format_currency(row["total"])
        ])
        
    # Add Total row
    data.append(["TOTAL", "", "", format_currency(total_debt)])
    
    # Table style - modern and clean
    table = Table(data, colWidths=[6.5*cm, 4*cm, 3*cm, 3.5*cm])
    t_style = TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('TOPPADDING', (0, 0), (-1, 0), 12),
        
        # Body
        ('ALIGN', (2, 1), (-1, -1), 'RIGHT'),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 1), (-1, -1), 8),
        ('TOPPADDING', (0, 1), (-1, -1), 8),
        
        # Alternating row colors
        *[('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8fafc')) for i in range(1, len(data)-1, 2)],
        
        # Grid lines
        ('LINEBELOW', (0, 0), (-1, -2), 1, colors.HexColor('#e2e8f0')),
        
        # Total row style (Outstanding!)
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ef4444')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 12),
        ('BOTTOMPADDING', (0, -1), (-1, -1), 12),
        ('TOPPADDING', (0, -1), (-1, -1), 12),
    ])
    table.setStyle(t_style)
    
    elements.append(table)
    
    # Footer
    elements.append(Spacer(1, 2*cm))
    footer_style = ParagraphStyle(
        'FooterStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.gray,
        alignment=1
    )
    elements.append(Paragraph("Ce document est généré automatiquement par le système MiroirPro.", footer_style))
    
    doc.build(elements)
    
    return str(filepath)
