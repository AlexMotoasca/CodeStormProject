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
from pypdf import PdfReader
from pdf2image import convert_from_path
from gemini_backend import get_gemini_backend
import google.generativeai as genai


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
        Extract text from scanned PDF using Gemini Vision API.

        Args:
            pdf_path: Path to the PDF file

        Returns:
            Extracted text from all pages using OCR
        """
        try:
            print(f"Starting scanned PDF extraction for: {pdf_path}")

            # Convert PDF pages to images
            try:
                images = convert_from_path(pdf_path)
                print(f"Successfully converted PDF to {len(images)} images")
            except Exception as convert_err:
                error_str = str(convert_err)
                print(f"ERROR: Could not convert PDF to images: {error_str}")

                if "poppler" in error_str.lower() or "Unable to get page count" in error_str:
                    print("\n⚠️ POPPLER NOT INSTALLED!")
                    print("Please install poppler to process scanned PDFs:")
                    print("Windows with Chocolatey: choco install poppler")
                    print("Windows Manual: Download from https://github.com/oschwartz10612/poppler-windows/releases/")
                    print("Then add C:\\poppler\\Library\\bin to your system PATH")
                    return None
                return None

            full_text = ""
            model = genai.GenerativeModel('gemini-2.5-flash')

            # Process ALL pages
            for page_num, image in enumerate(images):
                try:
                    print(f"Processing page {page_num + 1}/{len(images)}")

                    # Convert PIL image to bytes
                    image_bytes = io.BytesIO()
                    image.save(image_bytes, format='PNG')
                    image_bytes.seek(0)
                    image_data = image_bytes.getvalue()

                    # Use Gemini to extract text from image
                    response = model.generate_content([
                        "Extract all text from this image. Preserve formatting as much as possible. Return only the extracted text:",
                        genai.types.Part(
                            text="",
                            inline_data=genai.types.Blob(mime_type="image/png", data=image_data)
                        )
                    ])

                    if response and response.text:
                        full_text += f"\n--- Page {page_num + 1} ---\n{response.text}\n"
                        print(f"✓ Page {page_num + 1} extracted successfully ({len(response.text)} chars)")
                    else:
                        print(f"⚠ Page {page_num + 1}: No text returned from Gemini")

                except Exception as page_error:
                    print(f"❌ Error processing page {page_num + 1}: {str(page_error)}")
                    continue

            print(f"Scanned PDF extraction complete. Total text length: {len(full_text)}")
            return full_text.strip() if full_text.strip() else None

        except Exception as e:
            print(f"ERROR extracting text from scanned PDF: {str(e)}")
            import traceback
            traceback.print_exc()
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
                method = 'gemini_ocr'
                if text is None:
                    return {
                        'success': False,
                        'text': None,
                        'page_count': page_count,
                        'is_scanned': is_scanned,
                        'method': method,
                        'error': '⚠️ Scanned PDF detected but Poppler is not installed. Install poppler: choco install poppler'
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
