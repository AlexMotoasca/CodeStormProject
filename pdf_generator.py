"""
PDF Generator Module (Pure ReportLab)
Zero Temp Files. Native Windows Fonts (Romanian Diacritics). Custom Table Parser.
Includes Smart Cell Splitting to prevent height limit crashes.
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

def clean_text_for_reportlab(text: str) -> str:
    """
    Curăță textul pentru motorul XML strict al ReportLab.
    """
    text = re.sub(r'<br\s*/?>', '[[BR]]', text, flags=re.IGNORECASE)
    text = text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    text = text.replace('[[BR]]', '<br/>')
    text = re.sub(r'\*\*(.*?)\*\*', r'<b>\1</b>', text)
    return text

def generate_pdf_from_text(text: str) -> bytes:
    """
    Parses Markdown text directly into PDF objects with smart row splitting.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40
    )

    # 1. Încărcăm fontul ARIAL direct din Windows
    font_path = r"C:\Windows\Fonts\arial.ttf"
    font_bold_path = r"C:\Windows\Fonts\arialbd.ttf"

    if os.path.exists(font_path) and os.path.exists(font_bold_path):
        pdfmetrics.registerFont(TTFont('ArialLocal', font_path))
        pdfmetrics.registerFont(TTFont('ArialLocal-Bold', font_bold_path))
        font_name = 'ArialLocal'
        font_bold = 'ArialLocal-Bold'
    else:
        font_name = 'Helvetica'
        font_bold = 'Helvetica-Bold'

    styles = getSampleStyleSheet()
    normal_style = ParagraphStyle(
        'RomanianNormal',
        parent=styles['Normal'],
        fontName=font_name,
        fontSize=11,
        leading=15
    )
    bold_style = ParagraphStyle(
        'RomanianBold',
        parent=styles['Normal'],
        fontName=font_bold,
        fontSize=11,
        leading=15
    )

    story = []
    lines = text.split('\n')
    in_table = False
    table_data = []

    for line in lines:
        line = line.strip()

        # Logica pentru tabele
        if line.startswith('|') and line.endswith('|'):
            in_table = True

            if re.match(r'^\|[\-\s:\|]+\|$', line):
                continue

            cols = [col.strip() for col in line.split('|')[1:-1]]
            cleaned_cols = [clean_text_for_reportlab(col) for col in cols]

            # SOLUȚIA PENTRU CRASH: Smart Cell Splitting
            # Spargem celulele masive în rânduri multiple pentru a permite tăierea paginii
            split_cols = []
            for col_text in cleaned_cols:
                sub_chunks = []
                # Spargem automat la tag-urile <br/> extrase de pymupdf4llm
                for br_chunk in col_text.split('<br/>'):
                    # Dacă o propoziție e extrem de lungă, o spargem și pe aia (max 900 caractere)
                    while len(br_chunk) > 900:
                        split_idx = br_chunk.rfind(' ', 0, 900)
                        if split_idx == -1: split_idx = 900
                        sub_chunks.append(br_chunk[:split_idx])
                        br_chunk = br_chunk[split_idx:].strip()
                    sub_chunks.append(br_chunk)
                split_cols.append(sub_chunks)

            # Câte rânduri noi trebuie să creăm din această singură linie Markdown?
            max_lines = max([len(c) for c in split_cols]) if split_cols else 1
            is_header = (len(table_data) == 0)

            # Construim noile rânduri
            for i in range(max_lines):
                row_data = []
                for col_splits in split_cols:
                    cell_text = col_splits[i].strip() if i < len(col_splits) else ""
                    style = bold_style if (is_header and i == 0) else normal_style
                    row_data.append(Paragraph(cell_text, style))
                table_data.append(row_data)
            continue

        else:
            if in_table and table_data:
                # Desenăm tabelul acum că l-am optimizat
                t = Table(table_data, splitByRow=1)
                t.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6e6e6')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.black),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('BOX', (0, 0), (-1, -1), 1, colors.black),
                ]))
                story.append(t)
                story.append(Spacer(1, 10))

            in_table = False
            table_data = []

        if line == "":
            story.append(Spacer(1, 8))
            continue

        safe_line = clean_text_for_reportlab(line)

        if safe_line.startswith('#'):
            safe_line = safe_line.lstrip('#').strip()
            story.append(Paragraph(safe_line, bold_style))
        else:
            story.append(Paragraph(safe_line, normal_style))

        story.append(Spacer(1, 4))

    if in_table and table_data:
        t = Table(table_data, splitByRow=1)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e6e6e6')),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BOX', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ]))
        story.append(t)

    # 4. Construim PDF-ul
    doc.build(story)
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes