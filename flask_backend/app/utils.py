"""Utility Functions - Error handling, validation, and response formatting."""
from functools import wraps
from flask import jsonify, request
import uuid
from datetime import datetime


class APIResponse:
    """Standard API response formatter."""
    
    @staticmethod
    def success(data=None, message="Success", status_code=200):
        """Return a success response."""
        response = {
            "success": True,
            "data": data,
            "error": None,
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        }
        return jsonify(response), status_code

    @staticmethod
    def error(error_code, message, details=None, status_code=400):
        """Return an error response."""
        response = {
            "success": False,
            "data": None,
            "error": {
                "code": error_code,
                "message": message,
                "details": details
            },
            "meta": {
                "timestamp": datetime.utcnow().isoformat(),
                "request_id": str(uuid.uuid4())
            }
        }
        return jsonify(response), status_code


def validate_pdf_upload(f):
    """Decorator to validate PDF file upload."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'file' not in request.files:
            return APIResponse.error(
                'MISSING_FILE',
                'No file part in request',
                status_code=400
            )
        
        file = request.files['file']
        
        if file.filename == '':
            return APIResponse.error(
                'EMPTY_FILENAME',
                'No selected file',
                status_code=400
            )
        
        if not file.filename.lower().endswith('.pdf'):
            return APIResponse.error(
                'INVALID_FILE_TYPE',
                'Only PDF files are allowed',
                details={'allowed': ['pdf']},
                status_code=400
            )
        
        return f(*args, **kwargs)
    return decorated_function


def validate_json_params(required_params=None):
    """Decorator to validate JSON request parameters."""
    if required_params is None:
        required_params = []
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not request.is_json:
                return APIResponse.error(
                    'INVALID_CONTENT_TYPE',
                    'Content-Type must be application/json',
                    status_code=400
                )
            
            data = request.get_json()
            
            missing_params = [param for param in required_params if param not in data]
            if missing_params:
                return APIResponse.error(
                    'MISSING_PARAMETERS',
                    f'Missing required parameters: {", ".join(missing_params)}',
                    details={'required': required_params, 'provided': list(data.keys())},
                    status_code=400
                )
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator


class ValidationUtils:
    """Validation utility functions."""
    
    @staticmethod
    def validate_pdf_id(pdf_id: str) -> bool:
        """Validate PDF ID format (UUID or similar)."""
        if not pdf_id or not isinstance(pdf_id, str):
            return False
        # Simple check - more sophisticated if using specific ID format
        return len(pdf_id) > 0 and len(pdf_id) < 256

    @staticmethod
    def validate_document_type(doc_type: str) -> bool:
        """Validate document type."""
        valid_types = ['FD', 'PI', 'OTHER']
        return doc_type in valid_types if doc_type else True

    @staticmethod
    def validate_analysis_type(analysis_type: str) -> bool:
        """Validate analysis type."""
        valid_types = ['generic', 'components', 'structure']
        return analysis_type in valid_types if analysis_type else True

    @staticmethod
    def validate_info_type(info_type: str) -> bool:
        """Validate info extraction type."""
        valid_types = ['dates', 'names', 'amounts', 'credits', 'hours']
        return info_type in valid_types if info_type else True


class ErrorHandler:
    """Error handling utilities."""
    
    @staticmethod
    def handle_database_error(error: Exception):
        """Handle database errors."""
        print(f"Database error: {str(error)}")
        return APIResponse.error(
            'DATABASE_ERROR',
            'Database operation failed',
            details={'error': str(error)},
            status_code=500
        )

    @staticmethod
    def handle_file_error(error: Exception):
        """Handle file operation errors."""
        print(f"File error: {str(error)}")
        return APIResponse.error(
            'FILE_ERROR',
            'File operation failed',
            details={'error': str(error)},
            status_code=500
        )

    @staticmethod
    def handle_gemini_error(error: Exception):
        """Handle Gemini API errors."""
        print(f"Gemini API error: {str(error)}")
        return APIResponse.error(
            'GEMINI_ERROR',
            'Gemini API call failed',
            details={'error': str(error)},
            status_code=503
        )

    @staticmethod
    def handle_parser_error(error: Exception):
        """Handle PDF parser errors."""
        print(f"Parser error: {str(error)}")
        return APIResponse.error(
            'PARSER_ERROR',
            'PDF parsing failed',
            details={'error': str(error)},
            status_code=400
        )

