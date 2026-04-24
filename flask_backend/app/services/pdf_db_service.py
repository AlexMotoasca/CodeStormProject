"""PDF Database Service - PDF storage and layout operations."""
import io
import re
from pathlib import Path
from typing import Tuple, List, Optional
import fitz  # PyMuPDF

from app.models import db, Document, PDFSpan


class PDFDBService:
    """Service for database-backed PDF operations."""

    @staticmethod
    def get_pdf_by_id(pdf_id: str) -> Optional[Document]:
        """Get PDF document from database."""
        return Document.query.get(pdf_id)

    @staticmethod
    def save_pdf_document(filename: str, pdf_bytes: bytes, document_type: str = None,
                         extracted_text: str = None, is_scanned: bool = None,
                         extraction_method: str = None, file_size_bytes: int = None) -> Document:
        """Save PDF document to database."""
        try:
            doc = Document(
                filename=filename,
                file_size_bytes=file_size_bytes or len(pdf_bytes),
                document_type=document_type,
                extracted_text=extracted_text,
                is_scanned=is_scanned,
                extraction_method=extraction_method
            )
            db.session.add(doc)
            db.session.commit()
            
            # Store binary in filesystem (optional: use S3 or DB BLOB)
            PDFDBService._store_pdf_file(doc.id, pdf_bytes)
            
            return doc
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to save PDF document: {str(e)}")

    @staticmethod
    def _store_pdf_file(pdf_id: str, pdf_bytes: bytes):
        """Store PDF binary to filesystem."""
        from config import Config
        upload_dir = Path(Config.UPLOAD_FOLDER)
        upload_dir.mkdir(parents=True, exist_ok=True)
        file_path = upload_dir / f"{pdf_id}.pdf"
        file_path.write_bytes(pdf_bytes)

    @staticmethod
    def _retrieve_pdf_file(pdf_id: str) -> Optional[bytes]:
        """Retrieve PDF binary from filesystem."""
        from config import Config
        file_path = Path(Config.UPLOAD_FOLDER) / f"{pdf_id}.pdf"
        if file_path.exists():
            return file_path.read_bytes()
        return None

    @staticmethod
    def list_pdf_names(limit: int = 50, offset: int = 0) -> Tuple[List[dict], int]:
        """List all PDF names from database."""
        try:
            query = Document.query.order_by(Document.upload_timestamp.desc())
            total = query.count()
            pdfs = query.limit(limit).offset(offset).all()
            
            return [pdf.to_dict() for pdf in pdfs], total
        except Exception as e:
            raise Exception(f"Failed to list PDFs: {str(e)}")

    @staticmethod
    def get_pdf_bytes(pdf_id: str) -> Optional[bytes]:
        """Get PDF binary data."""
        return PDFDBService._retrieve_pdf_file(pdf_id)

    @staticmethod
    def update_pdf_bytes(pdf_id: str, pdf_bytes: bytes) -> bool:
        """Update PDF binary and document."""
        try:
            doc = Document.query.get(pdf_id)
            if not doc:
                return False
            
            doc.file_size_bytes = len(pdf_bytes)
            doc.last_modified = db.func.now()
            db.session.commit()
            
            PDFDBService._store_pdf_file(pdf_id, pdf_bytes)
            return True
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to update PDF: {str(e)}")

    @staticmethod
    def extract_text_and_layout(pdf_id: str) -> Tuple[str, List[dict]]:
        """Extract text and layout information from PDF."""
        try:
            pdf_bytes = PDFDBService.get_pdf_bytes(pdf_id)
            if not pdf_bytes:
                raise Exception(f"PDF not found: {pdf_id}")
            
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            spans = []
            lines = []

            for page_index, page in enumerate(doc):
                data = page.get_text("dict")
                for block in data.get("blocks", []):
                    if block.get("type") != 0:
                        continue

                    for line in block.get("lines", []):
                        line_parts = []
                        for span in line.get("spans", []):
                            raw_text = span.get("text", "")
                            if not raw_text:
                                continue

                            bbox_vals = span.get("bbox", (0.0, 0.0, 0.0, 0.0))
                            bbox = (
                                float(bbox_vals[0]),
                                float(bbox_vals[1]),
                                float(bbox_vals[2]),
                                float(bbox_vals[3]),
                            )

                            spans.append({
                                'page_index': page_index,
                                'bbox': bbox,
                                'font_size': float(span.get("size", 11.0)),
                                'color': int(span.get("color", 0)),
                                'text': raw_text
                            })
                            line_parts.append(raw_text)

                        if line_parts:
                            lines.append("".join(line_parts))

            doc.close()
            text = "\n".join(lines).strip()
            return text, spans

        except Exception as e:
            raise Exception(f"Failed to extract text and layout: {str(e)}")

    @staticmethod
    def _chunk_text_for_spans(edited_text: str, templates: List[dict]) -> List[str]:
        """Chunk edited text proportionally to original spans."""
        normalized = " ".join(edited_text.replace("\r", "").split())
        if not normalized:
            return [""] * len(templates)

        lengths = [max(1, len(item.get('text', ''))) for item in templates]
        total = sum(lengths)
        target = len(normalized)

        chunk_sizes = [max(1, round(target * length / total)) for length in lengths]

        drift = sum(chunk_sizes) - target
        idx = len(chunk_sizes) - 1
        while drift > 0 and idx >= 0:
            if chunk_sizes[idx] > 1:
                chunk_sizes[idx] -= 1
                drift -= 1
            else:
                idx -= 1

        idx = len(chunk_sizes) - 1
        while drift < 0 and idx >= 0:
            chunk_sizes[idx] += 1
            drift += 1
            idx -= 1
            if idx < 0:
                idx = len(chunk_sizes) - 1

        chunks = []
        pos = 0
        for size in chunk_sizes:
            chunks.append(normalized[pos:pos + size])
            pos += size

        return chunks

    @staticmethod
    def regenerate_pdf_with_layout(pdf_id: str, edited_text: str, templates: List[dict]) -> bytes:
        """Regenerate PDF with edited text while preserving layout."""
        try:
            pdf_bytes = PDFDBService.get_pdf_bytes(pdf_id)
            if not pdf_bytes:
                raise Exception(f"PDF not found: {pdf_id}")

            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            chunks = PDFDBService._chunk_text_for_spans(edited_text, templates)
            
            BLACK_TEXT_COLOR = (0.0, 0.0, 0.0)

            for span, new_text in zip(templates, chunks):
                page_idx = span.get('page_index', 0)
                bbox_tuple = span.get('bbox', (0, 0, 0, 0))
                
                page = doc[page_idx]
                rect = fitz.Rect(bbox_tuple)

                # White out the original text
                page.draw_rect(rect, fill=(1, 1, 1), color=(1, 1, 1), overlay=True)
                # Insert new text
                page.insert_textbox(
                    rect,
                    new_text,
                    fontsize=max(6.0, span.get('font_size', 11.0)),
                    fontname="helv",
                    color=BLACK_TEXT_COLOR,
                    align=fitz.TEXT_ALIGN_LEFT,
                    render_mode=0,
                    stroke_opacity=1,
                    fill_opacity=1,
                )

            out = doc.tobytes()
            doc.close()
            return out

        except Exception as e:
            raise Exception(f"Failed to regenerate PDF with layout: {str(e)}")

    @staticmethod
    def delete_pdf(pdf_id: str) -> bool:
        """Delete PDF from database and filesystem."""
        try:
            doc = Document.query.get(pdf_id)
            if not doc:
                return False
            
            db.session.delete(doc)
            db.session.commit()
            
            # Delete file from filesystem
            from config import Config
            file_path = Path(Config.UPLOAD_FOLDER) / f"{pdf_id}.pdf"
            if file_path.exists():
                file_path.unlink()
            
            return True
        except Exception as e:
            db.session.rollback()
            raise Exception(f"Failed to delete PDF: {str(e)}")


# Global instance
pdf_db_service = PDFDBService()


def get_pdf_db_service() -> PDFDBService:
    """Get the PDF database service instance."""
    return pdf_db_service

