"""Document Comparison API Routes - Filesystem Based."""
from flask import Blueprint, request
from app.services.comparison_service import get_comparison_service
from app.services.pdf_filesystem_service import get_pdf_filesystem_service
from app.utils import APIResponse, validate_json_params, ValidationUtils, ErrorHandler

bp = Blueprint('comparison', __name__, url_prefix='/api/comparison')

comparison_svc = get_comparison_service()
pdf_fs = get_pdf_filesystem_service()


@bp.route('/compare-fd-pi', methods=['POST'])
@validate_json_params(['fd_id', 'pi_id'])
def compare_fd_pi():
    """Compare FD (Fișa Disciplinei) with PI (Plan Învățământ)."""
    try:
        data = request.get_json()
        fd_id = data.get('fd_id')
        pi_id = data.get('pi_id')
        
        # Validate parameters
        if not ValidationUtils.validate_pdf_id(fd_id) or not ValidationUtils.validate_pdf_id(pi_id):
            return APIResponse.error(
                'INVALID_PDF_ID',
                'Invalid PDF ID format',
                status_code=400
            )
        
        # Get FD document
        fd_doc = pdf_fs.get_pdf_by_id(fd_id)
        if not fd_doc or not fd_doc.get('extracted_text'):
            return APIResponse.error(
                'NOT_FOUND',
                'FD PDF or extracted text not found',
                status_code=404
            )
        
        # Get PI document
        pi_doc = pdf_fs.get_pdf_by_id(pi_id)
        if not pi_doc or not pi_doc.get('extracted_text'):
            return APIResponse.error(
                'NOT_FOUND',
                'PI PDF or extracted text not found',
                status_code=404
            )
        
        # Perform comparison
        import time
        start_time = time.time()
        
        comparison_result = comparison_svc.compare_fd_pi(fd_doc.get('extracted_text'), pi_doc.get('extracted_text'))
        
        processing_time = int((time.time() - start_time) * 1000)
        
        if not comparison_result.get('success'):
            return ErrorHandler.handle_gemini_error(Exception(comparison_result.get('error', 'Comparison failed')))
        
        return APIResponse.success(
            data={
                'status': comparison_result.get('status', 'UNKNOWN'),
                'analysis': comparison_result.get('analysis'),
                'processing_time_ms': processing_time
            }
        )
    except Exception as e:
        return ErrorHandler.handle_gemini_error(e)


@bp.route('/history/<fd_id>/<pi_id>', methods=['GET'])
def comparison_history(fd_id, pi_id):
    """Get comparison history between two documents."""
    try:
        # Validate parameters
        if not ValidationUtils.validate_pdf_id(fd_id) or not ValidationUtils.validate_pdf_id(pi_id):
            return APIResponse.error(
                'INVALID_PDF_ID',
                'Invalid PDF ID format',
                status_code=400
            )
        
        # Query comparison history
        comparisons = ComparisonResult.query.filter_by(
            fd_id=fd_id,
            pi_id=pi_id
        ).order_by(ComparisonResult.created_at.desc()).limit(10).all()
        
        return APIResponse.success(
            data={
                'comparisons': [c.to_dict() for c in comparisons]
            }
        )
    except Exception as e:
        return ErrorHandler.handle_database_error(e)

