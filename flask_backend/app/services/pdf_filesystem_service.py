"""Filesystem-based PDF service - No database required."""
import os
import json
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pypdf
import io


class PDFFilesystemService:
    """Service for managing PDFs from filesystem."""

    def __init__(self, pdf_directory: str = "../PDFs"):
        """Initialize with PDFs directory."""
        self.pdf_dir = Path(pdf_directory)
        self.metadata_file = self.pdf_dir / ".metadata.json"
        self.metadata = self._load_metadata()

    def _load_metadata(self) -> Dict:
        """Load metadata from disk."""
        if self.metadata_file.exists():
            try:
                with open(self.metadata_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_metadata(self):
        """Save metadata to disk."""
        try:
            with open(self.metadata_file, 'w', encoding='utf-8') as f:
                json.dump(self.metadata, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Warning: Could not save metadata: {str(e)}")

    def list_pdfs(self) -> List[Dict]:
        """List all PDFs in directory."""
        pdfs = []
        if not self.pdf_dir.exists():
            return pdfs

        for pdf_file in sorted(self.pdf_dir.glob("*.pdf")):
            pdf_id = pdf_file.stem  # filename without extension
            try:
                file_size = pdf_file.stat().st_size
                
                # Get page count
                reader = pypdf.PdfReader(pdf_file)
                page_count = len(reader.pages)
                
                # Get metadata if exists
                pdf_meta = self.metadata.get(pdf_id, {})
                
                pdfs.append({
                    'id': pdf_id,
                    'filename': pdf_file.name,
                    'file_size_bytes': file_size,
                    'pages': page_count,
                    'document_type': pdf_meta.get('document_type'),
                    'extracted_text_preview': pdf_meta.get('extracted_text_preview', '')[:300],
                    'is_scanned': pdf_meta.get('is_scanned'),
                    'extraction_method': pdf_meta.get('extraction_method')
                })
            except Exception as e:
                print(f"Error processing {pdf_file.name}: {str(e)}")
                continue

        return pdfs

    def get_pdf_by_id(self, pdf_id: str) -> Optional[Dict]:
        """Get PDF details by ID."""
        pdf_file = self.pdf_dir / f"{pdf_id}.pdf"
        
        if not pdf_file.exists():
            return None

        try:
            file_size = pdf_file.stat().st_size
            reader = pypdf.PdfReader(pdf_file)
            page_count = len(reader.pages)
            
            pdf_meta = self.metadata.get(pdf_id, {})
            
            return {
                'id': pdf_id,
                'filename': pdf_file.name,
                'file_size_bytes': file_size,
                'pages': page_count,
                'document_type': pdf_meta.get('document_type'),
                'is_scanned': pdf_meta.get('is_scanned'),
                'extraction_method': pdf_meta.get('extraction_method'),
                'extracted_text': pdf_meta.get('extracted_text', ''),
                'extracted_text_preview': pdf_meta.get('extracted_text_preview', '')
            }
        except Exception as e:
            return None

    def get_pdf_bytes(self, pdf_id: str) -> Optional[bytes]:
        """Get PDF binary data."""
        pdf_file = self.pdf_dir / f"{pdf_id}.pdf"
        
        if pdf_file.exists():
            try:
                return pdf_file.read_bytes()
            except Exception as e:
                print(f"Error reading PDF: {str(e)}")
                return None
        return None

    def save_extracted_text(self, pdf_id: str, extracted_text: str, 
                           is_scanned: bool = False, method: str = 'text_extraction',
                           document_type: str = None):
        """Save extracted text metadata for a PDF."""
        pdf_file = self.pdf_dir / f"{pdf_id}.pdf"
        
        if not pdf_file.exists():
            return False

        preview = extracted_text[:500] if extracted_text else ""
        
        self.metadata[pdf_id] = {
            'extracted_text': extracted_text,
            'extracted_text_preview': preview,
            'is_scanned': is_scanned,
            'extraction_method': method,
            'document_type': document_type
        }
        
        self._save_metadata()
        return True

    def extract_text_and_layout(self, pdf_id: str) -> Tuple[str, List[Dict]]:
        """Extract text and layout from PDF."""
        pdf_bytes = self.get_pdf_bytes(pdf_id)
        if not pdf_bytes:
            raise Exception(f"PDF not found: {pdf_id}")

        text_lines = []
        spans = []
        
        try:
            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))
            
            for page_num, page in enumerate(reader.pages):
                text = page.extract_text()
                if text:
                    text_lines.append(text)
                    # Simple span representation based on page
                    spans.append({
                        'page_index': page_num,
                        'bbox': [0, 0, 100, 100],  # Simplified
                        'font_size': 12.0,
                        'color': 0,
                        'text': text[:200]
                    })
            
            return "\n".join(text_lines), spans
        except Exception as e:
            raise Exception(f"Failed to extract text: {str(e)}")

    def regenerate_pdf_with_layout(self, pdf_id: str, edited_text: str, 
                                   templates: List[Dict]) -> bytes:
        """Regenerate PDF with edited text (simplified)."""
        pdf_bytes = self.get_pdf_bytes(pdf_id)
        if not pdf_bytes:
            raise Exception(f"PDF not found: {pdf_id}")

        # For now, return the original PDF
        # Full implementation would require PDF manipulation library
        print(f"Note: PDF regeneration not fully implemented. Returning original PDF.")
        return pdf_bytes

    def delete_analysis_cache(self, pdf_id: str):
        """Delete cached analysis for a PDF."""
        if pdf_id in self.metadata:
            del self.metadata[pdf_id]
            self._save_metadata()


# Global instance
pdf_filesystem_service = PDFFilesystemService(pdf_directory="../PDFs")


def get_pdf_filesystem_service() -> PDFFilesystemService:
    """Get the PDF filesystem service instance."""
    return pdf_filesystem_service

