"""PDF Parsing Service - Enhanced PDF parser with OCR support."""
import os
import io
import tempfile
from pypdf import PdfReader

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
    pytesseract.pytesseract.pytesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class PDFParserService:
    """Enhanced PDF parser with support for scanned documents."""

    def extract_text_from_regular_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from regular (non-scanned) PDF."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            full_text = ""
            pages_with_text = 0

            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text and text.strip():
                        full_text += f"\n--- Page {page_num + 1} ---\n{text}\n"
                        pages_with_text += 1
                except Exception as page_err:
                    print(f"Warning: Could not extract text from page {page_num + 1}: {str(page_err)}")
                    continue

            print(f"Extracted text from {pages_with_text} pages")
            return full_text.strip() if full_text.strip() else None
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return None

    def is_scanned_pdf(self, pdf_bytes: bytes) -> bool:
        """Detect if a PDF is scanned (image-based)."""
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            if reader.pages:
                first_page_text = reader.pages[0].extract_text()
                return len(first_page_text.strip()) < 100
            return False
        except Exception as e:
            print(f"Error checking PDF type: {str(e)}")
            return True

    def extract_text_from_scanned_pdf(self, pdf_bytes: bytes) -> str:
        """Extract text from scanned PDF using Tesseract OCR."""
        if not TESSERACT_AVAILABLE:
            print("❌ Tesseract not available.")
            return None

        try:
            if not PYMUPDF_AVAILABLE:
                print("❌ PyMuPDF not available for PDF conversion.")
                return None

            print("Using PyMuPDF for PDF conversion...")
            pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
            full_text = ""

            for page_num in range(len(pdf_document)):
                try:
                    print(f"Processing page {page_num + 1}/{len(pdf_document)}")
                    page = pdf_document[page_num]
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                    
                    img_data = pix.tobytes("ppm")
                    image = Image.open(io.BytesIO(img_data))
                    
                    text = pytesseract.image_to_string(image)
                    
                    if text.strip():
                        full_text += f"\n--- Page {page_num + 1} ---\n{text}\n"
                        print(f"✓ Page {page_num + 1} extracted ({len(text)} chars)")
                    else:
                        print(f"⚠ No text found on page {page_num + 1}")

                except Exception as page_err:
                    print(f"Error processing page {page_num + 1}: {str(page_err)}")
                    continue

            pdf_document.close()

            if full_text.strip():
                print(f"✓ OCR extraction complete. Total text: {len(full_text)} chars")
                return full_text.strip()
            else:
                print("⚠ No text extracted from any page")
                return None

        except Exception as e:
            print(f"Error in OCR extraction: {str(e)}")
            return None

    def parse_pdf(self, pdf_bytes: bytes) -> dict:
        """
        Parse a PDF file (regular or scanned) and extract text.
        
        Args:
            pdf_bytes: Binary PDF data
            
        Returns:
            Dictionary with extraction results
        """
        try:
            reader = PdfReader(io.BytesIO(pdf_bytes))
            page_count = len(reader.pages)

            # Check if PDF is scanned
            is_scanned = self.is_scanned_pdf(pdf_bytes)

            # Extract text using appropriate method
            if is_scanned:
                text = self.extract_text_from_scanned_pdf(pdf_bytes)
                method = 'tesseract_ocr'
                if text is None:
                    return {
                        'success': False,
                        'text': None,
                        'page_count': page_count,
                        'is_scanned': is_scanned,
                        'method': method,
                        'error': 'Failed to extract text using Tesseract OCR.'
                    }
            else:
                text = self.extract_text_from_regular_pdf(pdf_bytes)
                method = 'text_extraction'
                if text is None:
                    return {
                        'success': False,
                        'text': None,
                        'page_count': page_count,
                        'is_scanned': is_scanned,
                        'method': method,
                        'error': 'PDF contains no extractable text.'
                    }

            return {
                'success': True,
                'text': text,
                'page_count': page_count,
                'is_scanned': is_scanned,
                'method': method,
                'error': None
            }

        except Exception as e:
            return {
                'success': False,
                'text': None,
                'page_count': 0,
                'is_scanned': None,
                'method': None,
                'error': f"Exception during parsing: {str(e)}"
            }


# Global parser instance
pdf_parser_service = PDFParserService()


def get_pdf_parser_service() -> PDFParserService:
    """Get the PDF parser service instance."""
    return pdf_parser_service

