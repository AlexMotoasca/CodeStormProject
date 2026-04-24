"""
Enhanced PDF Parser with Scanned Document Support

This module handles:
- Text extraction from regular PDFs
- OCR for scanned PDFs using Gemini Vision API
- Integration with Chainlit UI
- Multi-page processing
"""

import os
import io
import tempfile
from pypdf import PdfReader
from gemini_backend import get_gemini_backend
import google.generativeai as genai

try:
    import pytesseract
    from PIL import Image
    TESSERACT_AVAILABLE = True
    # Set Tesseract path to the installed location
    pytesseract.pytesseract.pytesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
except ImportError:
    TESSERACT_AVAILABLE = False

# Try to import pdf2image for converting PDF pages to images
try:
    from pdf2image import convert_from_path
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

# Try to import PyMuPDF for PDF to image conversion (no Poppler needed)
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False


class PDFParser:
    """Enhanced PDF parser with support for scanned documents."""

    def __init__(self):
        """Initialize the PDF parser with Gemini backend."""
        self.gemini = get_gemini_backend()

    def extract_text_from_regular_pdf(self, pdf_path: str) -> str:
        """
        Extract text from a regular (non-scanned) PDF.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text from all pages
        """
        try:
            reader = PdfReader(pdf_path)
            full_text = ""
            pages_with_text = 0

            # Extract text from ALL pages
            for page_num, page in enumerate(reader.pages):
                try:
                    text = page.extract_text()
                    if text and text.strip():  # Only add if text exists
                        full_text += f"\n--- Page {page_num + 1} ---\n{text}\n"
                        pages_with_text += 1
                except Exception as page_err:
                    print(f"Warning: Could not extract text from page {page_num + 1}: {str(page_err)}")
                    continue

            print(f"Extracted text from {pages_with_text} pages")
            # If no text found in any page, return None
            return full_text.strip() if full_text.strip() else None
        except Exception as e:
            print(f"Error extracting text from PDF: {str(e)}")
            return None

    def is_scanned_pdf(self, pdf_path: str) -> bool:
        """
        Detect if a PDF is scanned (image-based).

        Args:
            pdf_path: Path to the PDF file

        Returns:
            True if PDF appears to be scanned, False otherwise
        """
        try:
            reader = PdfReader(pdf_path)

            # Check first page for text content
            if reader.pages:
                first_page_text = reader.pages[0].extract_text()
                # If very little text is extracted, likely scanned
                return len(first_page_text.strip()) < 100
            return False
        except Exception as e:
            print(f"Error checking PDF type: {str(e)}")
            return True  # Assume scanned if error

    def extract_text_from_scanned_pdf_gemini(self, pdf_path: str) -> str:
        """
        Extract text from scanned PDF using Tesseract OCR.
        Converts PDF pages to images and applies OCR.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text from all pages using OCR
        """
        if not TESSERACT_AVAILABLE:
            print("❌ Tesseract not available. Install with: pip install pytesseract pillow")
            return None

        try:
            print(f"Starting scanned PDF extraction for: {pdf_path}")
            print("Converting PDF pages to images and applying Tesseract OCR...")

            # Try PyMuPDF first (no Poppler dependency)
            if PYMUPDF_AVAILABLE:
                return self._extract_with_pymupdf(pdf_path)
            # Then try pdf2image if available
            elif PDF2IMAGE_AVAILABLE:
                return self._extract_with_pdf2image(pdf_path)
            # Fall back to manual extraction
            else:
                print("⚠ No PDF to image converter available. Attempting manual extraction...")
                return self._extract_with_manual_method(pdf_path)

        except Exception as e:
            print(f"ERROR extracting text with Tesseract: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_with_pymupdf(self, pdf_path: str) -> str:
        """
        Extract text using PyMuPDF (fitz) to convert pages to PIL images.
        This method doesn't require Poppler.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text or None
        """
        try:
            print("Using PyMuPDF for PDF conversion...")

            # Open PDF with PyMuPDF
            pdf_document = fitz.open(pdf_path)
            full_text = ""

            for page_num in range(len(pdf_document)):
                try:
                    print(f"Processing page {page_num + 1}/{len(pdf_document)}")

                    # Get page
                    page = pdf_document[page_num]

                    # Render page to image (PNG)
                    pix = page.get_pixmap(matrix=fitz.Matrix(2, 2), alpha=False)  # 2x zoom for better OCR

                    # Convert pixmap to PIL Image
                    img_data = pix.tobytes("ppm")
                    image = Image.open(io.BytesIO(img_data))

                    # Apply Tesseract OCR to the image
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
            print(f"Error in PyMuPDF extraction: {str(e)}")
            import traceback
            traceback.print_exc()
            return None

    def _extract_with_pdf2image(self, pdf_path: str) -> str:
        """
        Extract text using pdf2image to convert pages to PIL images.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text or None
        """
        try:
            print("Using pdf2image for PDF conversion...")

            # Convert PDF pages to images
            images = convert_from_path(pdf_path, dpi=150)
            full_text = ""

            for page_num, image in enumerate(images, 1):
                try:
                    print(f"Processing page {page_num}/{len(images)}")

                    # Apply Tesseract OCR to the image
                    text = pytesseract.image_to_string(image)

                    if text.strip():
                        full_text += f"\n--- Page {page_num} ---\n{text}\n"
                        print(f"✓ Page {page_num} extracted ({len(text)} chars)")
                    else:
                        print(f"⚠ No text found on page {page_num}")

                except Exception as page_err:
                    print(f"Error processing page {page_num}: {str(page_err)}")
                    continue

            if full_text.strip():
                print(f"✓ OCR extraction complete. Total text: {len(full_text)} chars")
                return full_text.strip()
            else:
                print("⚠ No text extracted from any page")
                return None

        except Exception as e:
            print(f"Error in pdf2image extraction: {str(e)}")
            return None

    def _extract_with_manual_method(self, pdf_path: str) -> str:
        """
        Fallback method to extract images from PDF manually.
        Less reliable than pdf2image.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text or None
        """
        try:
            reader = PdfReader(pdf_path)
            full_text = ""

            for page_num, page in enumerate(reader.pages, 1):
                try:
                    print(f"Processing page {page_num}/{len(reader.pages)}")

                    # Try to extract images from page
                    if "/Resources" not in page:
                        print(f"⚠ No resources on page {page_num}")
                        continue

                    resources = page["/Resources"]
                    if "/XObject" not in resources:
                        print(f"⚠ No XObject on page {page_num}")
                        continue

                    xObject = resources["/XObject"].get_object()
                    page_text = ""

                    for obj_name in xObject:
                        try:
                            obj_ref = xObject[obj_name]

                            # Only process image objects
                            if obj_ref["/Subtype"] != "/Image":
                                continue

                            # Get image data
                            image_data = obj_ref.get_data()
                            width = int(obj_ref["/Width"])
                            height = int(obj_ref["/Height"])

                            # Try different image modes
                            for mode in ["RGB", "RGBA", "L", "P"]:
                                try:
                                    if mode == "RGB" and len(image_data) < width * height * 3:
                                        continue
                                    if mode == "RGBA" and len(image_data) < width * height * 4:
                                        continue
                                    if mode == "L" and len(image_data) < width * height:
                                        continue

                                    image = Image.frombytes(mode, (width, height), image_data)

                                    # Convert to RGB for Tesseract
                                    if image.mode != "RGB":
                                        image = image.convert("RGB")

                                    # Run OCR
                                    text = pytesseract.image_to_string(image)
                                    if text.strip():
                                        page_text += text + "\n"
                                        break

                                except Exception:
                                    continue

                        except Exception as obj_err:
                            continue

                    if page_text.strip():
                        full_text += f"\n--- Page {page_num} ---\n{page_text}\n"
                        print(f"✓ Page {page_num} extracted ({len(page_text)} chars)")
                    else:
                        print(f"⚠ No images found on page {page_num}")

                except Exception as page_err:
                    print(f"Error on page {page_num}: {str(page_err)}")
                    continue

            if full_text.strip():
                print(f"✓ Manual extraction complete. Total: {len(full_text)} chars")
                return full_text.strip()
            else:
                print("⚠ No text extracted")
                return None

        except Exception as e:
            print(f"Error in manual extraction: {str(e)}")
            return None

    def parse_pdf(self, pdf_path: str) -> dict:
        """
        Parse a PDF file (regular or scanned) and extract text.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Dictionary with extraction results
        """
        if not os.path.exists(pdf_path):
            return {
                'success': False,
                'text': None,
                'page_count': 0,
                'is_scanned': None,
                'method': None,
                'error': f"File not found: {pdf_path}"
            }

        try:
            reader = PdfReader(pdf_path)
            page_count = len(reader.pages)

            # Check if PDF is scanned
            is_scanned = self.is_scanned_pdf(pdf_path)

            # Extract text using appropriate method
            if is_scanned:
                text = self.extract_text_from_scanned_pdf_gemini(pdf_path)
                method = 'tesseract_ocr'
                if text is None:
                    return {
                        'success': False,
                        'text': None,
                        'page_count': page_count,
                        'is_scanned': is_scanned,
                        'method': method,
                        'error': 'Failed to extract text using Tesseract OCR. Make sure Tesseract is installed.'
                    }
            else:
                text = self.extract_text_from_regular_pdf(pdf_path)
                method = 'text_extraction'
                if text is None:
                    return {
                        'success': False,
                        'text': None,
                        'page_count': page_count,
                        'is_scanned': is_scanned,
                        'method': method,
                        'error': 'PDF contains no extractable text. The file may be empty or corrupted.'
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

    def save_to_file(self, text: str, output_path: str = "output.txt") -> bool:
        """
        Save extracted text to a file.

        Args:
            text: Text to save
            output_path: Path to output file

        Returns:
            True if successful, False otherwise
        """
        try:
            with open(output_path, "w", encoding="utf-8") as file:
                file.write(text)
            return True
        except Exception as e:
            print(f"Error saving to file: {str(e)}")
            return False


# Global parser instance
pdf_parser = PDFParser()


def get_pdf_parser() -> PDFParser:
    """Get the global PDF parser instance."""
    return pdf_parser


# Example usage (for testing)
if __name__ == '__main__':
    parser = PDFParser()

    # Example: Parse a PDF
    result = parser.parse_pdf('PDFs/fisa_disciplina.pdf')

    if result['success']:
        print(f"✅ PDF parsed successfully!")
        print(f"Pages: {result['page_count']}")
        print(f"Scanned: {result['is_scanned']}")
        print(f"Method: {result['method']}")
        print(f"\nExtracted Text Preview:\n{result['text'][:500]}...")

        # Save to file
        if parser.save_to_file(result['text']):
            print("\n✅ Text saved to output.txt")
    else:
        print(f"❌ Error: {result['error']}")
