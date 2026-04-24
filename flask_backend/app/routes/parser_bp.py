"""PDF Parser API Routes - Filesystem Based."""
from flask import Blueprint, request
from app.services.pdf_parser_service import get_pdf_parser_service
from app.services.pdf_filesystem_service import get_pdf_filesystem_service
from app.utils import APIResponse, validate_json_params, ValidationUtils, ErrorHandler

bp = Blueprint('parser', __name__, url_prefix='/api/parser')

pdf_parser = get_pdf_parser_service()
pdf_fs = get_pdf_filesystem_service()


@bp.route('/parse', methods=['POST'])
@validate_json_params(['pdf_id'])
def parse_pdf():
    """Parse a single PDF."""
    try:
        data = request.get_json()
        pdf_id = data.get('pdf_id')
        force_ocr = data.get('force_ocr', False)
        
        # Validate PDF ID
        if not ValidationUtils.validate_pdf_id(pdf_id):
            return APIResponse.error(
                'INVALID_PDF_ID',
                'Invalid PDF ID format',
                status_code=400
            )
        
        # Get PDF bytes
        pdf_bytes = pdf_fs.get_pdf_bytes(pdf_id)
        if not pdf_bytes:
            return APIResponse.error(
                'NOT_FOUND',
                'PDF not found',
                status_code=404
            )
        
        # Parse PDF
        import time
        start_time = time.time()
        parse_result = pdf_parser.parse_pdf(pdf_bytes)
        extraction_time = int((time.time() - start_time) * 1000)
        
        if not parse_result.get('success'):
            return APIResponse.error(
                'PARSER_ERROR',
                'Failed to parse PDF',
                details={'error': parse_result.get('error')},
                status_code=400
            )
        
        # Save metadata for this PDF
        pdf_fs.save_extracted_text(
            pdf_id,
            parse_result.get('text', ''),
            is_scanned=parse_result.get('is_scanned'),
            method=parse_result.get('method')
        )
        
        return APIResponse.success(
            data={
                'text': parse_result.get('text'),
                'page_count': parse_result.get('page_count'),
                'is_scanned': parse_result.get('is_scanned'),
                'method': parse_result.get('method'),
                'extraction_time_ms': extraction_time
            }
        )
    except Exception as e:
        return ErrorHandler.handle_parser_error(e)


@bp.route('/detect-type', methods=['POST'])
@validate_json_params(['pdf_id'])
def detect_pdf_type():
    """Detect if PDF is scanned or regular."""
    try:
        data = request.get_json()
        pdf_id = data.get('pdf_id')
        
        # Validate PDF ID
        if not ValidationUtils.validate_pdf_id(pdf_id):
            return APIResponse.error(
                'INVALID_PDF_ID',
                'Invalid PDF ID format',
                status_code=400
            )
        
        # Get PDF bytes
        pdf_bytes = pdf_fs.get_pdf_bytes(pdf_id)
        if not pdf_bytes:
            return APIResponse.error(
                'NOT_FOUND',
                'PDF not found',
                status_code=404
            )
        
        # Detect type
        is_scanned = pdf_parser.is_scanned_pdf(pdf_bytes)
        
        return APIResponse.success(
            data={
                'is_scanned': is_scanned,
                'confidence': 0.9 if is_scanned else 0.85
            }
        )
    except Exception as e:
        return ErrorHandler.handle_parser_error(e)


@bp.route('/parse-batch', methods=['POST'])
@validate_json_params(['pdf_ids'])
def parse_batch():
    """Parse multiple PDFs at once."""
    try:
        data = request.get_json()
        pdf_ids = data.get('pdf_ids', [])
        labels = data.get('labels', [])
        
        if not isinstance(pdf_ids, list) or len(pdf_ids) < 2:
            return APIResponse.error(
                'INVALID_REQUEST',
                'At least 2 PDF IDs required',
                status_code=400
            )
        
        # Validate all PDF IDs
        for pdf_id in pdf_ids:
            if not ValidationUtils.validate_pdf_id(pdf_id):
                return APIResponse.error(
                    'INVALID_PDF_ID',
                    f'Invalid PDF ID format: {pdf_id}',
                    status_code=400
                )
        
        results = []
        for idx, pdf_id in enumerate(pdf_ids):
            # Get PDF bytes
            pdf_bytes = pdf_fs.get_pdf_bytes(pdf_id)
            if not pdf_bytes:
                results.append({
                    'pdf_id': pdf_id,
                    'error': 'PDF not found',
                    'success': False
                })
                continue
            
            # Parse PDF
            parse_result = pdf_parser.parse_pdf(pdf_bytes)
            
            if parse_result.get('success'):
                pdf_fs.save_extracted_text(
                    pdf_id,
                    parse_result.get('text', ''),
                    is_scanned=parse_result.get('is_scanned'),
                    method=parse_result.get('method'),
                    document_type=labels[idx] if idx < len(labels) else None
                )
                
                results.append({
                    'pdf_id': pdf_id,
                    'label': labels[idx] if idx < len(labels) else None,
                    'text': parse_result.get('text'),
                    'page_count': parse_result.get('page_count'),
                    'is_scanned': parse_result.get('is_scanned'),
                    'method': parse_result.get('method'),
                    'success': True
                })
            else:
                results.append({
                    'pdf_id': pdf_id,
                    'error': parse_result.get('error'),
                    'success': False
                })
        
        return APIResponse.success(
            data={
                'results': results
            }
        )
    except Exception as e:
        return ErrorHandler.handle_parser_error(e)

