# CodeStorm Flask Backend - Complete API Endpoint Reference

## Overview
This document provides a complete reference of all RESTful API endpoints created for the CodeStorm Flask Backend.

---

## 📋 Table of Contents
1. [PDF Management Endpoints](#pdf-management)
2. [PDF Parsing Endpoints](#pdf-parsing)
3. [Gemini AI Endpoints](#gemini-ai)
4. [Document Comparison Endpoints](#document-comparison)
5. [PDF Editing Endpoints](#pdf-editing)
6. [Health & System Endpoints](#health-system)

---

## PDF Management

### 1. Upload PDF
**Endpoint:** `POST /api/pdf/upload`

**Description:** Upload a new PDF file to the system.

**Request:**
- **Content-Type:** `multipart/form-data`
- **Headers:** None required
- **Body:**
  ```
  file: <binary PDF file>
  document_type: "FD" | "PI" | "OTHER" (optional)
  description: "string" (optional)
  ```

**Response (201 Created):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "document.pdf",
    "file_size_bytes": 245123,
    "document_type": "FD",
    "pages": 12,
    "is_scanned": false,
    "extraction_method": "text_extraction",
    "upload_timestamp": "2024-01-15T10:30:00"
  },
  "error": null
}
```

**Error Responses:**
- `400 Bad Request` - Missing file or invalid type
- `500 Internal Server Error` - Parse or database error

---

### 2. List All PDFs
**Endpoint:** `GET /api/pdf/list`

**Description:** Retrieve paginated list of all PDFs in database.

**Request:**
- **Query Parameters:**
  ```
  limit: integer (1-100, default: 50)
  offset: integer (default: 0)
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "pdfs": [
      {
        "id": "550e8400-e29b-41d4-a716-446655440000",
        "filename": "fisa_disciplina.pdf",
        "file_size_bytes": 245123,
        "document_type": "FD",
        "pages": 12,
        "is_scanned": false,
        "extraction_method": "text_extraction",
        "upload_timestamp": "2024-01-15T10:30:00",
        "last_modified": "2024-01-15T10:35:00"
      }
    ],
    "pagination": {
      "total": 150,
      "limit": 50,
      "offset": 0
    }
  },
  "error": null
}
```

---

### 3. Get PDF Details
**Endpoint:** `GET /api/pdf/{pdf_id}`

**Description:** Get detailed information about a specific PDF including full extracted text.

**Request:**
- **Path Parameters:**
  ```
  pdf_id: UUID string
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "fisa_disciplina.pdf",
    "file_size_bytes": 245123,
    "document_type": "FD",
    "pages": 12,
    "is_scanned": false,
    "extraction_method": "text_extraction",
    "upload_timestamp": "2024-01-15T10:30:00",
    "extracted_text": "Full text content here...",
    "extracted_text_preview": "Full text content here..."
  },
  "error": null
}
```

**Error Responses:**
- `404 Not Found` - PDF not found
- `400 Bad Request` - Invalid PDF ID

---

### 4. Download PDF Binary
**Endpoint:** `GET /api/pdf/{pdf_id}/download`

**Description:** Download the PDF file as a binary attachment.

**Request:**
- **Path Parameters:**
  ```
  pdf_id: UUID string
  ```

**Response (200 OK):**
- **Content-Type:** `application/pdf`
- **Body:** PDF binary file

**Error Responses:**
- `404 Not Found` - PDF not found

---

### 5. Delete PDF
**Endpoint:** `DELETE /api/pdf/{pdf_id}`

**Description:** Delete a PDF from database and storage.

**Request:**
- **Path Parameters:**
  ```
  pdf_id: UUID string
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "message": "PDF deleted successfully"
  },
  "error": null
}
```

**Error Responses:**
- `404 Not Found` - PDF not found
- `500 Internal Server Error` - Deletion failed

---

## PDF Parsing

### 6. Parse Single PDF
**Endpoint:** `POST /api/parser/parse`

**Description:** Parse a PDF and extract text content.

**Request:**
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "pdf_id": "550e8400-e29b-41d4-a716-446655440000",
    "force_ocr": false
  }
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "text": "--- Page 1 ---\nExtracted text content...\n--- Page 2 ---\n...",
    "page_count": 12,
    "is_scanned": false,
    "method": "text_extraction",
    "extraction_time_ms": 1250
  },
  "error": null
}
```

**Error Responses:**
- `400 Bad Request` - Invalid PDF ID or parsing failed
- `404 Not Found` - PDF not found

---

### 7. Detect PDF Type
**Endpoint:** `POST /api/parser/detect-type`

**Description:** Detect whether a PDF is scanned (image-based) or contains regular text.

**Request:**
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "pdf_id": "550e8400-e29b-41d4-a716-446655440000"
  }
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "is_scanned": false,
    "confidence": 0.85
  },
  "error": null
}
```

---

### 8. Parse Batch (Multiple PDFs)
**Endpoint:** `POST /api/parser/parse-batch`

**Description:** Parse multiple PDFs at once (e.g., FD and PI together).

**Request:**
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "pdf_ids": [
      "550e8400-e29b-41d4-a716-446655440000",
      "660e8400-e29b-41d4-a716-446655440111"
    ],
    "labels": ["FD", "PI"]
  }
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "results": [
      {
        "pdf_id": "550e8400-e29b-41d4-a716-446655440000",
        "label": "FD",
        "text": "extracted text...",
        "page_count": 12,
        "is_scanned": false,
        "method": "text_extraction",
        "success": true
      },
      {
        "pdf_id": "660e8400-e29b-41d4-a716-446655440111",
        "label": "PI",
        "text": "extracted text...",
        "page_count": 20,
        "is_scanned": false,
        "method": "text_extraction",
        "success": true
      }
    ]
  },
  "error": null
}
```

**Error Responses:**
- `400 Bad Request` - Invalid request format
- `404 Not Found` - One or more PDFs not found

---

## Gemini AI

### 9. Analyze PDF
**Endpoint:** `POST /api/gemini/analyze`

**Description:** Analyze PDF content using Gemini AI with optional query.

**Request:**
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "pdf_id": "550e8400-e29b-41d4-a716-446655440000",
    "query": "What are the learning objectives?",
    "analysis_type": "generic"
  }
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "analysis": "Detailed analysis text from Gemini...",
    "processing_time_ms": 3450,
    "tokens_used": 250
  },
  "error": null
}
```

**Error Responses:**
- `400 Bad Request` - Invalid parameters
- `404 Not Found` - PDF not found
- `503 Service Unavailable` - Gemini API unavailable

---

### 10. Check Missing Components (Academic Audit)
**Endpoint:** `POST /api/gemini/check-components`

**Description:** Validate Fișa Disciplinei for completeness and math errors. Performs academic audit.

**Request:**
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "pdf_id": "550e8400-e29b-41d4-a716-446655440000"
  }
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "status": "INVALID",
    "math_errors": [
      {
        "rule": "Ore/săptămână = Curs + Seminar/Lab",
        "expected": "45",
        "found": "43",
        "details": "Mismatch in total hours per week"
      }
    ],
    "structural_errors": [
      {
        "section": "Evaluare",
        "issue": "Missing evaluation criteria",
        "details": "No minimum standard defined"
      }
    ],
    "missing_components": [
      "Bibliografie secundară",
      "Semnături finale"
    ],
    "warnings": [
      "Credit hours exceed typical range"
    ]
  },
  "error": null
}
```

**Error Responses:**
- `400 Bad Request` - Invalid PDF ID
- `404 Not Found` - PDF not found
- `503 Service Unavailable` - Gemini API unavailable

---

### 11. Summarize PDF
**Endpoint:** `POST /api/gemini/summarize`

**Description:** Generate a summary of PDF content.

**Request:**
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "pdf_id": "550e8400-e29b-41d4-a716-446655440000"
  }
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "summary": "This document describes the course objectives, content structure, and evaluation methods...",
    "key_points": [
      "Course covers advanced programming concepts",
      "Evaluation through projects and exams",
      "Practical lab sessions included"
    ]
  },
  "error": null
}
```

---

### 12. Extract Information
**Endpoint:** `POST /api/gemini/extract-info`

**Description:** Extract specific types of information from PDF.

**Request:**
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "pdf_id": "550e8400-e29b-41d4-a716-446655440000",
    "info_type": "credits"
  }
  ```

**Info Types:**
- `dates` - Extract dates
- `names` - Extract person/organization names
- `amounts` - Extract numerical amounts
- `credits` - Extract ECTS credits
- `hours` - Extract hour counts

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "extracted": [
      {
        "type": "credits",
        "value": "5 ECTS",
        "context": "Total course credits"
      },
      {
        "type": "credits",
        "value": "3 ECTS",
        "context": "Lab component"
      }
    ],
    "total_extracted": 2
  },
  "error": null
}
```

---

## Document Comparison

### 13. Compare FD with PI
**Endpoint:** `POST /api/comparison/compare-fd-pi`

**Description:** Compare Fișa Disciplinei with Plan Învățământ documents.

**Request:**
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "fd_id": "550e8400-e29b-41d4-a716-446655440000",
    "pi_id": "660e8400-e29b-41d4-a716-446655440111"
  }
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "status": "INCONSISTENT",
    "analysis": "📊 RAPORT COMPARATIV FD vs PI\n================================\n\n🔍 STATUS GENERAL: INCONSISTENT\n\n📋 STATISTICI:\n- Câmpuri care se potrivesc: 8\n- Inconsistențe totale: 3\n\n❌ ERORI CRITICE:\n\n1. **Ore Curs**\n  - Valoare în FD: 30\n  - Valoare în PI: 28\n  - Problemă: Oras nu se potrivesc\n  - Sugestie: Verificați planul de învățământ\n\n⚠️ AVERTISMENTE:\n...",
    "processing_time_ms": 5200
  },
  "error": null
}
```

**Error Responses:**
- `400 Bad Request` - Invalid PDF IDs
- `404 Not Found` - One or both PDFs not found
- `503 Service Unavailable` - Gemini API unavailable

---

### 14. Get Comparison History
**Endpoint:** `GET /api/comparison/history/{fd_id}/{pi_id}`

**Description:** Retrieve previous comparisons between two documents.

**Request:**
- **Path Parameters:**
  ```
  fd_id: UUID string
  pi_id: UUID string
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "comparisons": [
      {
        "id": "770e8400-e29b-41d4-a716-446655440222",
        "fd_id": "550e8400-e29b-41d4-a716-446655440000",
        "pi_id": "660e8400-e29b-41d4-a716-446655440111",
        "comparison_status": "INCONSISTENT",
        "summary": "3 mismatches found in course hours...",
        "created_at": "2024-01-15T10:30:00"
      }
    ]
  },
  "error": null
}
```

---

## PDF Editing

### 15. Extract Layout Information
**Endpoint:** `POST /api/pdf-edit/extract-layout`

**Description:** Extract text and layout information for PDF editing.

**Request:**
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "pdf_id": "550e8400-e29b-41d4-a716-446655440000"
  }
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "text": "Full document text...",
    "spans": [
      {
        "span_id": "0",
        "page_index": 0,
        "bbox": [100.5, 200.3, 400.2, 225.1],
        "font_size": 12.0,
        "color": 0,
        "text": "Original text in span"
      }
    ]
  },
  "error": null
}
```

---

### 16. Regenerate PDF with Edited Text
**Endpoint:** `POST /api/pdf-edit/regenerate`

**Description:** Regenerate PDF with edited text while preserving layout.

**Request:**
- **Content-Type:** `application/json`
- **Body:**
  ```json
  {
    "pdf_id": "550e8400-e29b-41d4-a716-446655440000",
    "edited_text": "New edited full text for the document...",
    "spans": [
      {
        "span_id": "0",
        "page_index": 0,
        "bbox": [100.5, 200.3, 400.2, 225.1],
        "font_size": 12.0,
        "color": 0,
        "text": "Original text in span"
      }
    ],
    "save_as_new": false
  }
  ```

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "regenerated_pdf_id": "550e8400-e29b-41d4-a716-446655440000",
    "preview_url": "/api/pdf/550e8400-e29b-41d4-a716-446655440000/download",
    "message": "PDF updated successfully"
  },
  "error": null
}
```

**Notes:**
- If `save_as_new` is `true`, creates a new PDF with "_edited" suffix
- If `save_as_new` is `false`, updates existing PDF

---

### 17. Get PDF Page Preview
**Endpoint:** `GET /api/pdf-edit/{pdf_id}/preview`

**Description:** Get preview of a specific PDF page as an image.

**Request:**
- **Path Parameters:**
  ```
  pdf_id: UUID string
  ```
- **Query Parameters:**
  ```
  page: integer (default: 1)
  ```

**Response (200 OK):**
- **Content-Type:** `image/png`
- **Body:** PNG image of the page

**Error Responses:**
- `404 Not Found` - PDF not found
- `400 Bad Request` - Invalid page number

---

## Health & System

### 18. Health Check
**Endpoint:** `GET /api/health`

**Description:** Check system and service health status.

**Request:**
- No parameters required

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "status": "healthy",
    "timestamp": "2024-01-15T10:30:00",
    "services": {
      "database": "connected",
      "gemini_api": "ready",
      "storage": "writable"
    }
  },
  "error": null
}
```

**Status Values:**
- `healthy` - All systems operational
- `degraded` - Some services unavailable, core functions work
- `unhealthy` - Major services down

---

### 19. System Statistics
**Endpoint:** `GET /api/health/stats`

**Description:** Get system usage statistics.

**Request:**
- No parameters required

**Response (200 OK):**
```json
{
  "success": true,
  "data": {
    "total_pdfs": 156,
    "total_storage_mb": 2345.67,
    "recent_analyses": 42,
    "uptime_seconds": 86400
  },
  "error": null
}
```

---

## Standard Error Codes

All error responses include a standardized error code:

| Code | HTTP Status | Description |
|------|------------|-------------|
| `NOT_FOUND` | 404 | Resource not found |
| `INVALID_PDF_ID` | 400 | Invalid PDF ID format |
| `INVALID_FILE_TYPE` | 400 | File is not a PDF |
| `MISSING_FILE` | 400 | File not provided in upload |
| `PARSER_ERROR` | 400 | PDF parsing failed |
| `DATABASE_ERROR` | 500 | Database operation failed |
| `GEMINI_ERROR` | 503 | Gemini API call failed |
| `FILE_ERROR` | 500 | File operation failed |
| `INTERNAL_ERROR` | 500 | Server error |
| `INVALID_CONTENT_TYPE` | 400 | Content-Type is not application/json |
| `MISSING_PARAMETERS` | 400 | Required parameters missing |
| `INVALID_REQUEST` | 400 | Invalid request format |
| `INVALID_DOCUMENT_TYPE` | 400 | Invalid document type |
| `INVALID_ANALYSIS_TYPE` | 400 | Invalid analysis type |
| `INVALID_INFO_TYPE` | 400 | Invalid information type |
| `METHOD_NOT_ALLOWED` | 405 | HTTP method not allowed |

---

## Authentication (Future)

Currently, all endpoints are unauthenticated. For production deployment, add:
- JWT token verification
- User authorization checks
- Request signing

---

## Rate Limiting (Recommended)

Consider implementing rate limiting on expensive operations:
- `/api/gemini/*` - 20 req/min per IP
- `/api/parser/parse-batch` - 10 req/min per IP
- `/api/pdf/upload` - 50 req/hour per IP

---

## Summary by Endpoint Category

| Category | Endpoints | Count |
|----------|-----------|-------|
| PDF Management | 5 | 5 |
| PDF Parsing | 3 | 3 |
| Gemini AI | 4 | 4 |
| Document Comparison | 2 | 2 |
| PDF Editing | 3 | 3 |
| Health & System | 2 | 2 |
| **TOTAL** | **19** | **19** |

---

## Usage Examples

### Example 1: Complete Workflow
```bash
# 1. Upload two PDFs
curl -X POST http://localhost:5000/api/pdf/upload \
  -F "file=@fd.pdf" \
  -F "document_type=FD"
# Response: fd_id

curl -X POST http://localhost:5000/api/pdf/upload \
  -F "file=@pi.pdf" \
  -F "document_type=PI"
# Response: pi_id

# 2. Parse both PDFs
curl -X POST http://localhost:5000/api/parser/parse-batch \
  -H "Content-Type: application/json" \
  -d '{"pdf_ids": ["fd_id", "pi_id"], "labels": ["FD", "PI"]}'

# 3. Compare documents
curl -X POST http://localhost:5000/api/comparison/compare-fd-pi \
  -H "Content-Type: application/json" \
  -d '{"fd_id": "fd_id", "pi_id": "pi_id"}'

# 4. Check FD for missing components
curl -X POST http://localhost:5000/api/gemini/check-components \
  -H "Content-Type: application/json" \
  -d '{"pdf_id": "fd_id"}'
```

---

**Last Updated:** January 15, 2024  
**API Version:** 1.0  
**Backend:** Flask 3.0.0  
**Database:** PostgreSQL 12+

