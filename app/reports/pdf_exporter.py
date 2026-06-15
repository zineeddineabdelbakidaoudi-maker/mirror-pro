"""PDF exporter for reports."""
from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from reportlab.lib.units import cm
from reportlab.lib.utils import ImageReader
from datetime import datetime
from typing import List, Dict, Any
from app.config import get_logo_path

class PdfExporter:
    @staticmethod
    def export(data: List[Dict[str, Any]], filepath: str, title: str) -> bool:
        if not data:
            return False

        try:
            doc = SimpleDocTemplate(filepath, pagesize=landscape(A4),
                                    rightMargin=1.5*cm, leftMargin=1.5*cm,
                                    topMargin=1.5*cm, bottomMargin=1.5*cm)
            elements = []
            styles = getSampleStyleSheet()
            
            # Title
            title_style = ParagraphStyle(
                'TitleStyle', parent=styles['Heading1'],
                fontSize=20, alignment=1, textColor=colors.HexColor('#2563eb'), fontName="Helvetica-Bold"
            )
            subtitle_style = ParagraphStyle(
                'SubTitleStyle', parent=styles['Normal'],
                fontSize=11, alignment=1, textColor=colors.HexColor('#64748b'), spaceAfter=15
            )
            
            # Header with logo
            header_data = []
            logo_path = get_logo_path()
            if logo_path.exists():
                try:
                    img_reader = ImageReader(str(logo_path))
                    orig_w, orig_h = img_reader.getSize()
                    aspect = orig_w / float(orig_h)
                    desired_h = 2.2 * cm
                    desired_w = desired_h * aspect
                    img = Image(str(logo_path), width=desired_w, height=desired_h)
                    header_data = [[img, Paragraph("<b>Atelier Glass Charaf</b><br/>Gestion Professionnelle", styles["Normal"])]]
                except Exception:
                    header_data = [[Paragraph("<b>Atelier Glass Charaf</b>", styles["Heading2"])]]
            else:
                header_data = [[Paragraph("<b>Atelier Glass Charaf</b>", styles["Heading2"])]]
                
            if header_data:
                t_header = Table(header_data, colWidths=[2.5*cm, 20*cm])
                t_header.setStyle(TableStyle([
                    ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ]))
                elements.append(t_header)
                elements.append(Spacer(1, 0.5*cm))

            elements.append(Paragraph(title, title_style))
            elements.append(Paragraph(f"Édité le {datetime.now().strftime('%d/%m/%Y à %H:%M')}", subtitle_style))
            elements.append(Spacer(1, 0.5*cm))

            # Table Data
            headers = list(data[0].keys())
            table_data = [headers]
            
            for row in data:
                table_data.append([str(row.get(h, "")) for h in headers])

            # Table Style
            t = Table(table_data, repeatRows=1)
            t_style = [
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#3b82f6')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 9),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 6),
                ('TOPPADDING', (0, 1), (-1, -1), 6),
                ('LINEBELOW', (0, 0), (-1, -1), 1, colors.HexColor('#e2e8f0')),
            ]
            
            # Alternating row colors
            for i in range(1, len(table_data)):
                if i % 2 == 1:
                    t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f8fafc')))
                else:
                    t_style.append(('BACKGROUND', (0, i), (-1, i), colors.white))
            
            t.setStyle(TableStyle(t_style))
            
            elements.append(t)
            doc.build(elements)
            return True
        except Exception as e:
            print(f"PDF Export Error: {e}")
            return False
