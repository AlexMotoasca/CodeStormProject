# CodeStorm Flask Backend

REST API backend for the CodeStorm PDF analysis system. Handles PDF uploads, parsing, OCR, Gemini AI analysis, and document comparison.

## Project Structure

```
flask_backend/
├── app/
│   ├── __init__.py              # Flask app factory
│   ├── models.py                # SQLAlchemy ORM models
│   ├── utils.py                 # Utility functions and decorators
│   ├── services/
│   │   ├── pdf_parser_service.py       # PDF parsing with OCR
│   │   ├── gemini_service.py           # Gemini AI integration
│   │   ├── pdf_db_service.py           # Database operations
│   │   └── comparison_service.py       # FD vs PI comparison
│   └── routes/
│       ├── pdf_bp.py            # PDF management endpoints
│       ├── parser_bp.py         # PDF parsing endpoints
│       ├── gemini_bp.py         # AI analysis endpoints
│       ├── comparison_bp.py     # Document comparison endpoints
│       ├── pdf_edit_bp.py       # PDF editing endpoints
│       └── health_bp.py         # Health check endpoints
├── config.py                    # Configuration management
├── run.py                       # Development server
├── wsgi.py                      # Production WSGI entry point
├── requirements.txt             # Python dependencies
└── .env.example                 # Environment variables template
```

## Installation

### Prerequisites

- Python 3.9+
- PostgreSQL 12+
- Tesseract OCR (optional, for scanned PDFs)

### Steps

1. Clone repository and navigate to flask_backend:
```bash
cd CodeStormProject/flask_backend
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/Scripts/activate  # On Windows
# or: source venv/bin/activate  # On Linux/Mac
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize database:
```bash
# Using Flask shell (or your migration tool)
python -c "from app import create_app; app = create_app(); app.app_context().push()"
```

## Running the Server

### Development
```bash
python run.py
```
Server will start at `http://localhost:5000`

### Production
```bash
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app
```

## API Endpoints Overview

### PDF Management (`/api/pdf/*`)
- `POST /api/pdf/upload` - Upload new PDF
- `GET /api/pdf/list` - List all PDFs
- `GET /api/pdf/{pdf_id}` - Get PDF details
- `GET /api/pdf/{pdf_id}/download` - Download PDF binary
- `DELETE /api/pdf/{pdf_id}` - Delete PDF

### PDF Parsing (`/api/parser/*`)
- `POST /api/parser/parse` - Parse single PDF
- `POST /api/parser/detect-type` - Detect if PDF is scanned
- `POST /api/parser/parse-batch` - Parse multiple PDFs

### Gemini AI (`/api/gemini/*`)
- `POST /api/gemini/analyze` - Analyze PDF with query
- `POST /api/gemini/check-components` - Academic audit (FD validation)
- `POST /api/gemini/summarize` - Summarize PDF content
- `POST /api/gemini/extract-info` - Extract specific information

### Document Comparison (`/api/comparison/*`)
- `POST /api/comparison/compare-fd-pi` - Compare FD with PI
- `GET /api/comparison/history/{fd_id}/{pi_id}` - Get comparison history

### PDF Editing (`/api/pdf-edit/*`)
- `POST /api/pdf-edit/extract-layout` - Extract text and layout
- `POST /api/pdf-edit/regenerate` - Regenerate PDF with edited text
- `GET /api/pdf-edit/{pdf_id}/preview` - Get PDF page preview

### Health & Status (`/api/health/*`)
- `GET /api/health` - Health check
- `GET /api/health/stats` - System statistics

## API Response Format

All endpoints return standardized JSON responses:

### Success Response (2xx)
```json
{
  "success": true,
  "data": {
    "id": "uuid",
    "...": "..."
  },
  "error": null,
  "meta": {
    "timestamp": "2024-01-01T00:00:00",
    "request_id": "uuid"
  }
}
```

### Error Response (4xx/5xx)
```json
{
  "success": false,
  "data": null,
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable message",
    "details": { "...": "..." }
  },
  "meta": {
    "timestamp": "2024-01-01T00:00:00",
    "request_id": "uuid"
  }
}
```

## Example Usage

### Upload PDF
```bash
curl -X POST http://localhost:5000/api/pdf/upload \
  -F "file=@document.pdf" \
  -F "document_type=FD"
```

### Parse PDF
```bash
curl -X POST http://localhost:5000/api/parser/parse \
  -H "Content-Type: application/json" \
  -d '{"pdf_id": "123e4567-e89b-12d3-a456-426614174000"}'
```

### Compare Documents
```bash
curl -X POST http://localhost:5000/api/comparison/compare-fd-pi \
  -H "Content-Type: application/json" \
  -d '{
    "fd_id": "fd-uuid",
    "pi_id": "pi-uuid"
  }'
```

## Configuration

### Environment Variables

See `.env.example` for all available options:
- `FLASK_ENV`: development/production/testing
- `SECRET_KEY`: Session secret (required for production)
- `DATABASE_URL`: PostgreSQL connection string
- `GEMINI_API_KEY`: Google Gemini API key
- `UPLOAD_MAX_MB`: Maximum file upload size
- `CORS_ORIGINS`: Allowed frontend origins
- `SESSION_TIMEOUT_MINS`: Session timeout in minutes

### Database Setup

1. **Create PostgreSQL database:**
```sql
CREATE DATABASE codestorm;
```

2. **Models are automatically created on first run**, or manually:
```python
from app import create_app
app = create_app()
with app.app_context():
    from app.models import db
    db.create_all()
```

## Services

### PDFParserService
Handles PDF text extraction and OCR for scanned documents.

**Key Methods:**
- `parse_pdf(pdf_bytes)` - Extract text from PDF
- `is_scanned_pdf(pdf_bytes)` - Detect if scanned
- `extract_text_from_scanned_pdf(pdf_bytes)` - OCR extraction

### GeminiService
Wrapper for Google's Gemini API for AI-powered analysis.

**Key Methods:**
- `generate_text(prompt)` - Generate text
- `analyze_pdf_content(pdf_text, query)` - Analyze with query
- `compare_pdfs(pdf1_text, pdf2_text)` - Compare documents
- `check_missing_components(pdf_text, pdf_name)` - Academic audit

### PDFDBService
Database operations for PDF storage and layout preservation.

**Key Methods:**
- `save_pdf_document()` - Save PDF to database
- `get_pdf_by_id()` - Retrieve PDF
- `extract_text_and_layout()` - Extract layout information
- `regenerate_pdf_with_layout()` - Regenerate with edited text

### ComparisonService
FD vs PI document comparison logic.

**Key Methods:**
- `compare_fd_pi(fd_text, pi_text)` - Compare documents
- `compare_fd_simple(text1, text2)` - Simple diff-based comparison

## Error Handling

All errors follow standardized format with specific error codes:
- `NOT_FOUND` (404): Resource not found
- `INVALID_PDF_ID` (400): Invalid PDF ID format
- `PARSER_ERROR` (400): PDF parsing failed
- `DATABASE_ERROR` (500): Database operation failed
- `GEMINI_ERROR` (503): Gemini API call failed
- `FILE_ERROR` (500): File operation failed
- `INTERNAL_ERROR` (500): Server error

## Security Notes

- **Authentication**: Currently unauthenticated. Add JWT in production
- **File Validation**: Only PDF files allowed
- **CORS**: Configured for frontend origins
- **Database**: Use environment variables for credentials
- **API Keys**: Never commit `.env` files

## Testing

```bash
# Run tests
pytest

# With coverage
pytest --cov=app tests/
```

## Performance Considerations

- PDF parsing is synchronous; consider async for large files
- Cache Gemini responses for identical queries
- Use PostgreSQL connection pooling
- Enable response compression
- Consider CDN for static file serving

## Deployment

### Heroku
```bash
# Set environment variables
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secret
heroku config:set DATABASE_URL=your-database-url
heroku config:set GEMINI_API_KEY=your-key

# Deploy
git push heroku main
```

### Docker
```bash
docker build -t codestorm-backend .
docker run -p 5000:5000 --env-file .env codestorm-backend
```

## Troubleshooting

### Database Connection Error
- Verify PostgreSQL is running
- Check DATABASE_URL in `.env`
- Ensure user has database creation permissions

### Tesseract Not Found
- Install Tesseract OCR
- Set correct path in environment
- Or use alternative OCR (Gemini Vision API)

### GEMINI_API_KEY Error
- Get API key from Google AI Studio
- Set in `.env` file
- Ensure no extra whitespace

### CORS Errors
- Add frontend URL to `CORS_ORIGINS` in `.env`
- Frontend must send proper Origin header

## Contributing

1. Create feature branch
2. Make changes
3. Run tests
4. Submit pull request

## License

MIT License - See LICENSE file

## Support

For issues or questions:
1. Check API documentation
2. Review error codes and messages
3. Check application logs
4. Submit issue with traceback

---

**API Documentation**: See planned React frontend for complete UI interaction patterns.

