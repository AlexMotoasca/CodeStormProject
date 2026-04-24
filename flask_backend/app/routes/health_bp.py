"""Health Check & System Status API Routes."""
from flask import Blueprint
from datetime import datetime
from app.models import db, Document
from app.utils import APIResponse

bp = Blueprint('health', __name__, url_prefix='/api/health')

import time
start_time = time.time()


@bp.route('', methods=['GET'])
def health_check():
    """Health check endpoint."""
    try:
        # Check database connection
        db.session.execute(db.text('SELECT 1'))
        db_status = 'connected'
    except Exception as e:
        print(f"Database connection error: {str(e)}")
        db_status = 'disconnected'
    
    # Check Gemini API
    try:
        from app.services.gemini_service import get_gemini_service
        gemini = get_gemini_service()
        # Simple test
        response = gemini.generate_text("Test")
        gemini_status = 'ready' if response and 'Error' not in response else 'unavailable'
    except Exception as e:
        print(f"Gemini API error: {str(e)}")
        gemini_status = 'unavailable'
    
    # Check storage
    try:
        from config import Config
        from pathlib import Path
        upload_dir = Path(Config.UPLOAD_FOLDER)
        upload_dir.mkdir(parents=True, exist_ok=True)
        # Try to write a test file
        test_file = upload_dir / '.health_check'
        test_file.write_text('test')
        test_file.unlink()
        storage_status = 'writable'
    except Exception as e:
        print(f"Storage error: {str(e)}")
        storage_status = 'error'
    
    return APIResponse.success(
        data={
            'status': 'healthy' if db_status == 'connected' else 'degraded',
            'timestamp': datetime.utcnow().isoformat(),
            'services': {
                'database': db_status,
                'gemini_api': gemini_status,
                'storage': storage_status
            }
        }
    )


@bp.route('/stats', methods=['GET'])
def system_stats():
    """Get system statistics."""
    try:
        total_pdfs = Document.query.count()
        
        # Calculate total storage
        total_storage_mb = 0
        pdfs = Document.query.all()
        for pdf in pdfs:
            if pdf.file_size_bytes:
                total_storage_mb += pdf.file_size_bytes
        total_storage_mb = total_storage_mb / (1024 * 1024)
        
        # Count recent analyses (last 24 hours)
        from datetime import timedelta
        cutoff_time = datetime.utcnow() - timedelta(hours=24)
        recent_analyses = Document.query.filter(
            Document.last_modified >= cutoff_time
        ).count()
        
        # Calculate uptime
        uptime_seconds = int(time.time() - start_time)
        
        return APIResponse.success(
            data={
                'total_pdfs': total_pdfs,
                'total_storage_mb': round(total_storage_mb, 2),
                'recent_analyses': recent_analyses,
                'uptime_seconds': uptime_seconds
            }
        )
    except Exception as e:
        print(f"Stats error: {str(e)}")
        return APIResponse.error(
            'STATS_ERROR',
            'Failed to retrieve system statistics',
            details={'error': str(e)},
            status_code=500
        )

