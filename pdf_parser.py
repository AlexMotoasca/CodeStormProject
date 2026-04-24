"""
Enhanced PDF Parser with Scanned Document Support and Markdown/Table Extraction

This module handles:
- Text extraction from regular PDFs
- OCR for scanned PDFs using Tesseract
- Markdown extraction (with tables) using pymupdf4llm
- Multi-page processing
"""

import os
import io
import tempfile
from pypdf import PdfReader
from gemini_backend import get_gemini_backend

# --- DEPENDENCIES OPTIONALE ---
try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
    pytesseract.pytesseract.pytesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except ImportError:
    TESSERACT_AVAILABLE = False

try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

try:
    import pymupdf4llm
    PYMUPDF4LLM_AVAILABLE = True
except ImportError:
    PYMUPDF4LLM_AVAILABLE = False


class PDFParser:
    """Enhanced PDF parser with support for scanned documents and Markdown structure."""

    def __init__(self):
        self.gemini = get_gemini_backend()

    def extract_markdown_with_tables(self, pdf_path: str) -> str:
        """
        Extract text keeping the structure and tables intact using Markdown.
        """
        if not PYMUPDF4LLM_AVAILABLE:
            print("❌ pymupdf4llm not available. Install with: pip install pymupdf4llm")
            return None

        try:
            print(f"Extracting Markdown structure for: {pdf_path}")
            md_text = pymupdf4llm.to_markdown(pdf_path)
            return md_text
        except Exception as e:
            print(f"Error extracting markdown: {str(e)}")
            return None

    def extract_text_from_regular_pdf(self, pdf_path: str) -> str:
        """Extract text from a regular (non-scanned) PDF."""
        try:
            reader = PdfReader(pdf_path)
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

            return full_text.strip() if full_text.strip() else None
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return None

    def is_scanned_pdf(self, pdf_path: str) -> bool:
        """Detect if a PDF is scanned (image-based)."""
        try:
            reader = PdfReader(pdf_path)
            if reader.pages:
                first_page_text = reader.pages[0].extract_text()
                return len(first_page_text.strip()) < 100
            return False
        except Exception as e:
            return True

    def extract_text_from_scanned_pdf_gemini(self, pdf_path: str) -> str:
        """Extract text from scanned PDF using Tesseract OCR."""
        if not TESSERACT_AVAILABLE:
            return None

        try:
            if PYMUPDF_AVAILABLE:
                return self._extract_with_pymupdf(pdf_path)
            elif PDF2IMAGE_AVAILABLE:
                return self._extract_with_pdf2image(pdf_path)
            else:
                return self._extract_with_manual_method(pdf_path)
        except Exception as e:
            return None

    def _extract_with_pymupdf(self, pdf_path: str) -> str:
        try:
            pdf_document = fitz.open(pdf_path)
            full_text = ""
            for page_num in range(len(pdf_document)):
                page = pdf_document[page_num]
                pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)
                img_data = pix.tobytes("ppm")
                image = Image.open(io.BytesIO(img_data))
                text = pytesseract.image_to_string(image)
                if text.strip():
                    full_text += f"\n--- Page {page_num + 1} ---\n{text}\n"
            pdf_document.close()
            return full_text.strip() if full_text.strip() else None
        except Exception:
            return None

    def _extract_with_pdf2image(self, pdf_path: str) -> str:
        try:
            images = convert_from_path(pdf_path, dpi=150)
            full_text = ""
            for page_num, image in enumerate(images, 1):
                text = pytesseract.image_to_string(image)
                if text.strip():
                    full_text += f"\n--- Page {page_num} ---\n{text}\n"
            return full_text.strip() if full_text.strip() else None
        except Exception:
            return None

    def _extract_with_manual_method(self, pdf_path: str) -> str:
        try:
            reader = PdfReader(pdf_path)
            full_text = ""
            for page_num, page in enumerate(reader.pages, 1):
                if "/Resources" not in page or "/XObject" not in page["/Resources"]:
                    continue
                xObject = page["/Resources"]["/XObject"].get_object()
                page_text = ""
                for obj_name in xObject:
                    obj_ref = xObject[obj_name]
                    if obj_ref["/Subtype"] != "/Image":
                        continue
                    try:
                        image_data = obj_ref.get_data()
                        width, height = int(obj_ref["/Width"]), int(obj_ref["/Height"])
                        for mode in ["RGB", "RGBA", "L", "P"]:
                            try:
                                image = Image.frombytes(mode, (width, height), image_data)
                                if image.mode != "RGB":
                                    image = image.convert("RGB")
                                text = pytesseract.image_to_string(image)
                                if text.strip():
                                    page_text += text + "\n"
                                    break
                            except Exception:
                                continue
                    except Exception:
                        continue
                if page_text.strip():
                    full_text += f"\n--- Page {page_num} ---\n{page_text}\n"
            return full_text.strip() if full_text.strip() else None
        except Exception:
            return None

    def parse_pdf(self, pdf_path: str, as_markdown: bool = False) -> dict:
        """
        Parse a PDF file.

        Args:
            pdf_path: Path to the PDF file
            as_markdown: If True, attempts to extract Markdown (preserves tables)
        """
        if not os.path.exists(pdf_path):
            return {'success': False, 'text': None, 'page_count': 0, 'is_scanned': None, 'method': None, 'error': f"File not found: {pdf_path}"}

        try:
            reader = PdfReader(pdf_path)
            page_count = len(reader.pages)
            is_scanned = self.is_scanned_pdf(pdf_path)

            # 1. MARKDOWN EXTRACTION (Păstrează tabelele)
            if as_markdown:
                text = self.extract_markdown_with_tables(pdf_path)
                if text:
                    return {'success': True, 'text': text, 'page_count': page_count, 'is_scanned': is_scanned, 'method': 'pymupdf4llm_markdown', 'error': None}
                # Dacă eșuează Markdown, cade înapoi la metodele normale...

            # 2. STANDARD EXTRACTION
            if is_scanned:
                text = self.extract_text_from_scanned_pdf_gemini(pdf_path)
                method = 'tesseract_ocr'
            else:
                text = self.extract_text_from_regular_pdf(pdf_path)
                method = 'text_extraction'

            if text is None:
                return {'success': False, 'text': None, 'page_count': page_count, 'is_scanned': is_scanned, 'method': method, 'error': 'Nu s-a putut extrage text din acest PDF.'}

            return {
                'success': True,
                'text': text,
                'page_count': page_count,
                'is_scanned': is_scanned,
                'method': method,
                'error': None
            }

        except Exception as e:
            return {'success': False, 'text': None, 'page_count': 0, 'is_scanned': None, 'method': None, 'error': f"Exception during parsing: {str(e)}"}

    def save_to_file(self, text: str, output_path: str = "output.txt") -> bool:
        try:
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(text)
            return True
        except Exception as e:
            return False


# Global parser instance
pdf_parser = PDFParser()

def get_pdf_parser() -> PDFParser:
    return pdf_parser