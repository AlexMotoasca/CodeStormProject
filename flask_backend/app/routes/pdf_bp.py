"""PDF Management API Routes - Filesystem Based."""
from flask import Blueprint, request, send_file
import io
from app.services.pdf_parser_service import get_pdf_parser_service
from app.services.pdf_filesystem_service import get_pdf_filesystem_service
from app.utils import APIResponse, validate_pdf_upload, validate_json_params, ValidationUtils, ErrorHandler

bp = Blueprint('pdf', __name__, url_prefix='/api/pdf')

pdf_parser = get_pdf_parser_service()
pdf_fs = get_pdf_filesystem_service()


@bp.route('/upload', methods=['POST'])
def upload_pdf():
    """Upload a new PDF file (note: for filesystem use, add PDFs to PDFs/ directory)."""
    return APIResponse.success(
        data={
            'message': 'Add PDF files directly to the PDFs/ directory',
            'instruction': 'Place your PDF files in: CodeStormProject/PDFs/'
        },
        status_code=200
    )


@bp.route('/list', methods=['GET'])
def list_pdfs():
    """List all PDF documents from PDFs directory."""
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validate parameters
        limit = min(limit, 100)
        offset = max(offset, 0)
        
        pdfs = pdf_fs.list_pdfs()
        total = len(pdfs)
        
        # Apply pagination
        paginated_pdfs = pdfs[offset:offset + limit]
        
        return APIResponse.success(
            data={
                'pdfs': paginated_pdfs,
                'pagination': {
                    'total': total,
                    'limit': limit,
                    'offset': offset
                }
            }
        )
    except Exception as e:
        return ErrorHandler.handle_file_error(e)


@bp.route('/<pdf_id>', methods=['GET'])
def get_pdf_details(pdf_id):
    """Get PDF details."""
    try:
        if not ValidationUtils.validate_pdf_id(pdf_id):
            return APIResponse.error(
                'INVALID_PDF_ID',
                'Invalid PDF ID format',
                status_code=400
            )
        
        doc = pdf_fs.get_pdf_by_id(pdf_id)
        if not doc:
            return APIResponse.error(
                'NOT_FOUND',
                'PDF not found',
                status_code=404
            )
        
        return APIResponse.success(data=doc)
    except Exception as e:
        return ErrorHandler.handle_file_error(e)


@bp.route('/<pdf_id>/download', methods=['GET'])
def download_pdf(pdf_id):
    """Download PDF binary."""
    try:
        if not ValidationUtils.validate_pdf_id(pdf_id):
            return APIResponse.error(
                'INVALID_PDF_ID',
                'Invalid PDF ID format',
                status_code=400
            )
        
        doc = pdf_fs.get_pdf_by_id(pdf_id)
        if not doc:
            return APIResponse.error(
                'NOT_FOUND',
                'PDF not found',
                status_code=404
            )
        
        pdf_bytes = pdf_fs.get_pdf_bytes(pdf_id)
        if not pdf_bytes:
            return APIResponse.error(
                'FILE_NOT_FOUND',
                'PDF file not found in storage',
                status_code=404
            )
        
        return send_file(
            io.BytesIO(pdf_bytes),
            mimetype='application/pdf',
            as_attachment=True,
            download_name=doc['filename']
        )
    except Exception as e:
        return ErrorHandler.handle_file_error(e)


@bp.route('/<pdf_id>', methods=['DELETE'])
def delete_pdf(pdf_id):
    """Delete PDF (remove from metadata cache)."""
    try:
        if not ValidationUtils.validate_pdf_id(pdf_id):
            return APIResponse.error(
                'INVALID_PDF_ID',
                'Invalid PDF ID format',
                status_code=400
            )
        
        doc = pdf_fs.get_pdf_by_id(pdf_id)
        if not doc:
            return APIResponse.error(
                'NOT_FOUND',
                'PDF not found',
                status_code=404
            )
        
        # Clear metadata cache for this PDF
        pdf_fs.delete_analysis_cache(pdf_id)
        
        return APIResponse.success(
            data={'message': 'PDF cache cleared. To delete files, remove from PDFs/ directory.'}
        )
    except Exception as e:
        return ErrorHandler.handle_file_error(e)

