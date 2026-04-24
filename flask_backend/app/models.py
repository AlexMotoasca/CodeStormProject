"""SQLAlchemy database models."""
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid

db = SQLAlchemy()


class Document(db.Model):
    """PDF Document model."""
    __tablename__ = 'documents'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    filename = db.Column(db.String(255), nullable=False, index=True)
    file_size_bytes = db.Column(db.Integer)
    document_type = db.Column(db.String(50), index=True)  # 'FD', 'PI', 'OTHER'
    extracted_text = db.Column(db.Text)  # Cached extracted text
    is_scanned = db.Column(db.Boolean)
    extraction_method = db.Column(db.String(50))  # 'text_extraction', 'tesseract_ocr'
    upload_timestamp = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_modified = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    created_by = db.Column(db.String(255), default='system')
    
    # Relationships
    spans = db.relationship('PDFSpan', backref='document', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, include_text=False):
        """Convert to dictionary."""
        data = {
            'id': self.id,
            'filename': self.filename,
            'file_size_bytes': self.file_size_bytes,
            'document_type': self.document_type,
            'pages': self.extracted_text.count('--- Page') if self.extracted_text else 0,
            'is_scanned': self.is_scanned,
            'extraction_method': self.extraction_method,
            'upload_timestamp': self.upload_timestamp.isoformat() if self.upload_timestamp else None,
            'last_modified': self.last_modified.isoformat() if self.last_modified else None,
        }
        if include_text:
            data['extracted_text'] = self.extracted_text
            data['extracted_text_preview'] = (self.extracted_text[:300] + '...') if self.extracted_text and len(self.extracted_text) > 300 else self.extracted_text
        return data


class PDFSpan(db.Model):
    """PDF text span with layout information (for editing & regeneration)."""
    __tablename__ = 'pdf_spans'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False, index=True)
    page_index = db.Column(db.Integer, nullable=False)
    bbox_x0 = db.Column(db.Float)  # Bounding box coordinates
    bbox_y0 = db.Column(db.Float)
    bbox_x1 = db.Column(db.Float)
    bbox_y1 = db.Column(db.Float)
    font_size = db.Column(db.Float)
    color = db.Column(db.Integer)
    original_text = db.Column(db.Text)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'span_id': self.id,
            'page_index': self.page_index,
            'bbox': [self.bbox_x0, self.bbox_y0, self.bbox_x1, self.bbox_y1],
            'font_size': self.font_size,
            'color': self.color,
            'text': self.original_text
        }


class ComparisonResult(db.Model):
    """Comparison results between FD and PI documents."""
    __tablename__ = 'comparison_results'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    fd_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False, index=True)
    pi_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False, index=True)
    comparison_status = db.Column(db.String(50))  # 'CONSISTENT', 'INCONSISTENT', 'NEEDS_REVIEW'
    critical_errors = db.Column(db.JSON)  # Stored as JSON
    warnings = db.Column(db.JSON)
    summary = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'fd_id': self.fd_id,
            'pi_id': self.pi_id,
            'comparison_status': self.comparison_status,
            'critical_errors': self.critical_errors,
            'warnings': self.warnings,
            'summary': self.summary,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }


class AnalysisResult(db.Model):
    """Gemini analysis results cache."""
    __tablename__ = 'analysis_results'
    
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    document_id = db.Column(db.String(36), db.ForeignKey('documents.id'), nullable=False, index=True)
    analysis_type = db.Column(db.String(50), nullable=False)  # 'components', 'summary', 'extract_info'
    analysis_query = db.Column(db.String(255))  # Optional query parameter
    result_data = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        """Convert to dictionary."""
        return {
            'id': self.id,
            'document_id': self.document_id,
            'analysis_type': self.analysis_type,
            'analysis_query': self.analysis_query,
            'result_data': self.result_data,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

