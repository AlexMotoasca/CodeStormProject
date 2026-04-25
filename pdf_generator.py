"""
PDF Generator Module - Advanced Form Layout
Handles dynamic column widths and Romanian diacritics.
"""
import io
import os
import re
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.units import cm

def clean_text_for_reportlab(text: str) -> str:
    text = re.sub(r'<br\s*/?>', '[[BR]]', text, flags=re.IGNORECASE)
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = text.replace('[[BR]]', '<br/>')
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return text

def generate_pdf_from_text(text: str) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=1.2*cm, leftMargin=1.2*cm, topMargin=1.2*cm, bottomMargin=1.2*cm
    )

    font_path = r"C:\Windows\Fonts\arial.ttf"
    font_bold_path = r"C:\Windows\Fonts\arialbd.ttf"

    if os.path.exists(font_path):
        pdfmetrics.registerFont(TTFont('Arial', font_path))
        pdfmetrics.registerFont(TTFont('Arial-Bold', font_bold_path))
        font_main, font_bold = 'Arial', 'Arial-Bold'
    else:
        font_main, font_bold = 'Helvetica', 'Helvetica-Bold'

    styles = getSampleStyleSheet()
    style_n = ParagraphStyle('Small', fontName=font_main, fontSize=8.5, leading=10)
    style_b = ParagraphStyle('SmallBold', fontName=font_bold, fontSize=8.5, leading=10)
    style_h = ParagraphStyle('Heading', fontName=font_bold, fontSize=11, leading=14, spaceBefore=10, spaceAfter=5)

    story = []
    lines = text.split('\n')
    table_data = []
    in_table = False

    for line in lines:
        line = line.strip()

        if line.startswith('|') and line.endswith('|'):
            in_table = True
            if re.match(r'^\|[\-\s:\|]+\|$', line): continue

            cols = [col.strip() for col in line.split('|')[1:-1]]
            row_data = []
            for i, col in enumerate(cols):
                clean_content = clean_text_for_reportlab(col)
                # Prima coloana e de obicei label-ul
                st = style_b if (i == 0 or len(cols) == 1) else style_n
                row_data.append(Paragraph(clean_content, st))
            table_data.append(row_data)
            continue
        else:
            if in_table and table_data:
                num_cols = len(table_data[0])
                total_w = 18.6 * cm # Lățime totală utilă

                # LOGICĂ DINAMICĂ DE COLOANE
                if num_cols == 2:
                    col_widths = [total_w * 0.35, total_w * 0.65]
                elif num_cols > 4:
                    # Pentru tabelele de ore (secțiunea 3), lăsăm coloanele să fie mici
                    first_w = total_w * 0.30
                    rest_w = (total_w - first_w) / (num_cols - 1)
                    col_widths = [first_w] + [rest_w] * (num_cols - 1)
                else:
                    col_widths = [total_w / num_cols] * num_cols

                t = Table(table_data, colWidths=col_widths, splitByRow=1)
                t.setStyle(TableStyle([
                    ('GRID', (0,0), (-1,-1), 0.5, colors.black),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('BACKGROUND', (0,0), (0,-1), colors.whitesmoke),
                    ('FONTSIZE', (0,0), (-1,-1), 8.5),
                    ('LEFTPADDING', (0,0), (-1,-1), 4),
                    ('RIGHTPADDING', (0,0), (-1,-1), 4),
                ]))
                story.append(t)
                story.append(Spacer(1, 4)) # Spațiu mic între tabelele sparte

            in_table, table_data = False, []

        if not line: continue
        if line.startswith('#'):
            story.append(Paragraph(clean_text_for_reportlab(line.lstrip('#').strip()), style_h))
        else:
            story.append(Paragraph(clean_text_for_reportlab(line), style_n))

    doc.build(story)
    return buffer.getvalue()