"""
PDF Generator Module

Handles the creation of new PDF documents from plain text.
"""
import io
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.pagesizes import A4


def generate_pdf_from_text(text: str) -> bytes:
    """
    Converts plain text into a formatted PDF byte stream.

    Args:
        text: The raw text to put into the PDF.

    Returns:
        bytes: The generated PDF file in byte format.
    """
    # Create an in-memory byte buffer
    buffer = io.BytesIO()

    # Set up the document
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=40,
        leftMargin=40,
        topMargin=40,
        bottomMargin=40
    )

    # Get standard styles
    styles = getSampleStyleSheet()
    normal_style = styles["Normal"]

    # Build the story (the content of the PDF)
    story = []

    # Process text line by line
    for line in text.split('\n'):
        # Skip completely empty lines if there are too many, or just keep them for spacing
        if line.strip() == "":
            story.append(Spacer(1, 10))
            continue

        # Escape XML characters that break reportlab (<, >, &)
        safe_line = line.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')

        # Add the line as a paragraph (this handles text wrapping automatically)
        story.append(Paragraph(safe_line, normal_style))
        story.append(Spacer(1, 4))  # Small space between paragraphs

    # Build the PDF
    doc.build(story)

    # Get the value from the buffer
    pdf_bytes = buffer.getvalue()
    buffer.close()

    return pdf_bytes