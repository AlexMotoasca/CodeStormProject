"""Gemini AI API Routes - Filesystem Based."""
from flask import Blueprint, request
from app.services.gemini_service import get_gemini_service
from app.services.pdf_filesystem_service import get_pdf_filesystem_service
from app.utils import APIResponse, validate_json_params, ValidationUtils, ErrorHandler

bp = Blueprint('gemini', __name__, url_prefix='/api/gemini')

gemini = get_gemini_service()
pdf_fs = get_pdf_filesystem_service()


@bp.route('/analyze', methods=['POST'])
@validate_json_params(['pdf_id'])
def analyze_pdf():
    """Analyze PDF content with optional query."""
    try:
        data = request.get_json()
        pdf_id = data.get('pdf_id')
        query = data.get('query')
        analysis_type = data.get('analysis_type', 'generic')
        
        # Validate parameters
        if not ValidationUtils.validate_pdf_id(pdf_id):
            return APIResponse.error(
                'INVALID_PDF_ID',
                'Invalid PDF ID format',
                status_code=400
            )
        
        if not ValidationUtils.validate_analysis_type(analysis_type):
            return APIResponse.error(
                'INVALID_ANALYSIS_TYPE',
                'Invalid analysis type',
                details={'allowed': ['generic', 'components', 'structure']},
                status_code=400
            )
        
        # Get PDF text
        doc = pdf_fs.get_pdf_by_id(pdf_id)
        if not doc or not doc.get('extracted_text'):
            return APIResponse.error(
                'NOT_FOUND',
                'PDF or extracted text not found',
                status_code=404
            )
        
        # Perform analysis
        import time
        start_time = time.time()
        
        if query:
            result = gemini.analyze_pdf_content(doc.get('extracted_text'), query)
        else:
            result = gemini.generate_text(f"Analyze this document:\n\n{doc.get('extracted_text', '')[:4000]}")
        
        processing_time = int((time.time() - start_time) * 1000)
        
        return APIResponse.success(
            data={
                'analysis': result,
                'processing_time_ms': processing_time,
                'tokens_used': len(result.split()) // 4  # Rough estimate
            }
        )
    except Exception as e:
        return ErrorHandler.handle_gemini_error(e)


@bp.route('/check-components', methods=['POST'])
@validate_json_params(['pdf_id'])
def check_components():
    """Check PDF for missing components (academic audit for FD)."""
    try:
        data = request.get_json()
        pdf_id = data.get('pdf_id')
        
        # Validate parameters
        if not ValidationUtils.validate_pdf_id(pdf_id):
            return APIResponse.error(
                'INVALID_PDF_ID',
                'Invalid PDF ID format',
                status_code=400
            )
        
        # Get PDF
        doc = pdf_fs.get_pdf_by_id(pdf_id)
        if not doc or not doc.get('extracted_text'):
            return APIResponse.error(
                'NOT_FOUND',
                'PDF or extracted text not found',
                status_code=404
            )
        
        # Check components
        result = gemini.check_missing_components(doc.get('extracted_text'), doc.get('filename'))
        
        if result.get('success'):
            analysis = result.get('analysis')
            if analysis:
                return APIResponse.success(
                    data={
                        'status': analysis.get('status', 'UNKNOWN'),
                        'math_errors': analysis.get('math_errors', []),
                        'structural_errors': analysis.get('structural_errors', []),
                        'missing_components': analysis.get('missing_components', []),
                        'warnings': analysis.get('general_warnings', [])
                    }
                )
            else:
                return APIResponse.success(
                    data={
                        'status': 'UNKNOWN',
                        'raw_response': result.get('raw_response'),
                        'note': 'Response could not be parsed as structured data'
                    }
                )
        else:
            return ErrorHandler.handle_gemini_error(Exception(result.get('error', 'Unknown error')))
    except Exception as e:
        return ErrorHandler.handle_gemini_error(e)


@bp.route('/summarize', methods=['POST'])
@validate_json_params(['pdf_id'])
def summarize_pdf():
    """Summarize PDF content."""
    try:
        data = request.get_json()
        pdf_id = data.get('pdf_id')
        
        # Validate parameters
        if not ValidationUtils.validate_pdf_id(pdf_id):
            return APIResponse.error(
                'INVALID_PDF_ID',
                'Invalid PDF ID format',
                status_code=400
            )
        
        # Get PDF text
        doc = pdf_fs.get_pdf_by_id(pdf_id)
        if not doc or not doc.get('extracted_text'):
            return APIResponse.error(
                'NOT_FOUND',
                'PDF or extracted text not found',
                status_code=404
            )
        
        # Generate summary
        summary = gemini.summarize_pdf(doc.get('extracted_text'))
        
        # Extract key points (simple splitting)
        key_points = [point.strip() for point in summary.split('\n') if point.strip() and len(point.strip()) > 10][:5]
        
        return APIResponse.success(
            data={
                'summary': summary,
                'key_points': key_points
            }
        )
    except Exception as e:
        return ErrorHandler.handle_gemini_error(e)


@bp.route('/extract-info', methods=['POST'])
@validate_json_params(['pdf_id', 'info_type'])
def extract_info():
    """Extract specific information from PDF."""
    try:
        data = request.get_json()
        pdf_id = data.get('pdf_id')
        info_type = data.get('info_type')
        
        # Validate parameters
        if not ValidationUtils.validate_pdf_id(pdf_id):
            return APIResponse.error(
                'INVALID_PDF_ID',
                'Invalid PDF ID format',
                status_code=400
            )
        
        if not ValidationUtils.validate_info_type(info_type):
            return APIResponse.error(
                'INVALID_INFO_TYPE',
                'Invalid info type',
                details={'allowed': ['dates', 'names', 'amounts', 'credits', 'hours']},
                status_code=400
            )
        
        # Get PDF text
        doc = pdf_fs.get_pdf_by_id(pdf_id)
        if not doc or not doc.get('extracted_text'):
            return APIResponse.error(
                'NOT_FOUND',
                'PDF or extracted text not found',
                status_code=404
            )
        
        # Extract information
        result = gemini.extract_key_information(doc.get('extracted_text'), info_type)
        
        # Parse result into structured format
        extracted_items = []
        for line in result.split('\n'):
            if line.strip() and len(line.strip()) > 3:
                extracted_items.append({
                    'type': info_type,
                    'value': line.strip(),
                    'context': ''
                })
        
        return APIResponse.success(
            data={
                'extracted': extracted_items[:50],  # Limit to 50 items
                'total_extracted': len(extracted_items)
            }
        )
    except Exception as e:
        return ErrorHandler.handle_gemini_error(e)

