# CodeStorm React Frontend - Complete Generation Prompt

## Project Overview

You are building a **React + TypeScript** frontend for the CodeStorm PDF analysis system. The backend is a Flask REST API running on `http://localhost:5000` that processes PDFs from a filesystem directory and uses Google's Gemini AI for analysis.

**Backend Stack:** Flask, PostgreSQL (not used), PyPDF, Google Gemini API
**Frontend Stack:** React 18+, TypeScript, Vite, Tailwind CSS / Material-UI
**Key Features:** PDF uploading, parsing, comparison, AI analysis, validation

---

## 📋 Project Structure

```
CodeStormProject-Frontend/
├── src/
│   ├── main.tsx                    # React entry point
│   ├── App.tsx                     # Main app component
│   ├── index.css
│   │
│   ├── components/
│   │   ├── PDFUploader/
│   │   │   ├── PDFUploader.tsx      # Upload interface
│   │   │   └── PDFUploader.module.css
│   │   │
│   │   ├── PDFListView/
│   │   │   ├── PDFListView.tsx      # List all PDFs
│   │   │   └── PDFListView.module.css
│   │   │
│   │   ├── PDFViewer/
│   │   │   ├── PDFViewer.tsx        # View & parse PDF
│   │   │   └── PDFViewer.module.css
│   │   │
│   │   ├── ComparisonView/
│   │   │   ├── ComparisonView.tsx   # FD vs PI comparison
│   │   │   └── ComparisonView.module.css
│   │   │
│   │   ├── ValidationChecker/
│   │   │   ├── ValidationChecker.tsx # Academic audit results
│   │   │   └── ValidationChecker.module.css
│   │   │
│   │   └── Common/
│   │       ├── LoadingSpinner.tsx
│   │       ├── ErrorAlert.tsx
│   │       ├── SuccessMessage.tsx
│   │       └── Header.tsx
│   │
│   ├── services/
│   │   ├── api.ts                  # Axios instance
│   │   ├── pdfService.ts           # PDF endpoints
│   │   ├── parserService.ts        # Parsing endpoints
│   │   ├── geminiService.ts        # AI analysis endpoints
│   │   └── comparisonService.ts    # Comparison endpoints
│   │
│   ├── hooks/
│   │   ├── usePDFUpload.ts         # PDF upload state
│   │   ├── usePDFList.ts           # List PDFs state
│   │   ├── usePDFParsing.ts        # Parsing state
│   │   ├── useComparison.ts        # Comparison state
│   │   └── useAnalysis.ts          # Analysis state
│   │
│   ├── types/
│   │   └── index.ts                # TypeScript interfaces
│   │
│   └── styles/
│       └── globals.css             # Global styles
│
├── public/
│   └── index.html
├── package.json
├── vite.config.ts
├── tsconfig.json
└── .env.example
```

---

## 🎯 Core Components to Build

### 1. **PDFUploader Component**
**Purpose:** Allow users to select and upload PDFs (note: backend reads from PDFs directory)
**Props:** None
**State:**
- `selectedPDFs: File[]`
- `isUploading: boolean`
- `error: string | null`

**Features:**
- Drag-and-drop zone for PDFs
- File input with multiple selection
- Display selected files
- Show upload progress
- Display success/error messages
- Display file size and type validation

**API Integration:**
```typescript
POST /api/pdf/list  // Get available PDFs after upload
```

---

### 2. **PDFListView Component**
**Purpose:** Display all available PDFs from the PDFs directory
**State:**
- `pdfs: PDFInfo[]`
- `isLoading: boolean`
- `error: string | null`
- `currentPage: number`
- `pageSize: number`

**Features:**
- Paginated table of PDFs
- Display columns: Filename, Pages, Type, Size, Upload Date
- Action buttons for each PDF:
  - 👁️ View
  - 🔍 Parse
  - ⚖️ Compare
  - 📊 Validate
  - 📥 Download
- Sort by columns
- Search/filter by filename or type
- Refresh button
- Total PDFs count

**API Integration:**
```typescript
GET /api/pdf/list?limit=50&offset=0  // List PDFs
GET /api/pdf/{id}                    // Get details
GET /api/pdf/{id}/download           // Download PDF
```

---

### 3. **PDFViewer Component**
**Purpose:** View and analyze a single PDF
**Props:**
- `pdfId: string`
- `mode: 'view' | 'parse' | 'edit'`
- `onClose: () => void`

**State:**
- `pdf: PDFData | null`
- `extractedText: string`
- `isLoading: boolean`
- `error: string | null`
- `activeTab: 'preview' | 'text' | 'metadata'`

**Features:**
- Display PDF preview (if library available)
- Display extracted text in tab
- Show PDF metadata (pages, type, size)
- Copy extracted text button
- Download extracted text as .txt
- Show parsing method (text_extraction vs OCR)
- Show file size and page count

**API Integration:**
```typescript
GET /api/pdf/{id}                   // Get PDF details
POST /api/parser/parse              // Parse PDF
GET /api/pdf-edit/{id}/preview      // Get preview image
```

---

### 4. **ComparisonView Component**
**Purpose:** Compare FD and PI documents side-by-side
**Props:**
- `fdId: string`
- `piId: string`
- `onClose: () => void`

**State:**
- `fdText: string`
- `piText: string`
- `comparisonResult: ComparisonResult | null`
- `isLoading: boolean`
- `error: string | null`

**Features:**
- Side-by-side document display
- Syntax highlighting for differences
- Display comparison status (CONSISTENT/INCONSISTENT/NEEDS_REVIEW)
- Show critical errors with badges
- Show warnings in collapsible sections
- Display summary text
- Export comparison report button
- Scroll sync between left and right panels

**API Integration:**
```typescript
POST /api/parser/parse-batch        // Parse both PDFs
POST /api/comparison/compare-fd-pi  // Get comparison
GET /api/comparison/history/{fd_id}/{pi_id}  // View history
```

**Response Example:**
```json
{
  "status": "INCONSISTENT",
  "analysis": "📊 RAPORT COMPARATIV FD vs PI\n...",
  "processing_time_ms": 5200
}
```

---

### 5. **ValidationChecker Component**
**Purpose:** Display academic audit results for Fișa Disciplinei
**Props:**
- `pdfId: string`
- `onClose: () => void`

**State:**
- `validationResult: ValidationResult | null`
- `isLoading: boolean`
- `error: string | null`

**Features:**
- Display overall status (VALID/INVALID with icon)
- Collapsible sections for:
  - **Math Errors:** List with rule, expected, found, details
  - **Structural Errors:** Section issues and details
  - **Missing Components:** CheckList of components
  - **General Warnings:** Warning list
- Color-coded badges (red for errors, yellow for warnings, green for OK)
- Export audit report button
- Recommendations display

**API Integration:**
```typescript
POST /api/gemini/check-components  // Run academic audit
```

**Response Example:**
```json
{
  "status": "INVALID",
  "math_errors": [
    {
      "rule": "Ore/săptămână = Curs + Seminar",
      "expected": "45",
      "found": "43",
      "details": "Mismatch"
    }
  ],
  "structural_errors": [...],
  "missing_components": ["Bibliografie", "Semnături"],
  "warnings": [...]
}
```

---

### 6. **Navigation / Header Component**
**Purpose:** Main navigation bar
**Features:**
- Logo and branding
- Navigation tabs:
  - Home
  - PDF Library
  - Compare Documents
  - Validate Document
  - About
- User menu (if auth added)
- Notification bell
- Status indicator for backend connection

---

## 🔌 API Service Layer

### `api.ts` - Axios Config
```typescript
import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:5000/api';

export const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for standardized error handling
api.interceptors.response.use(
  response => response.data,
  error => {
    throw {
      code: error.response?.data?.error?.code,
      message: error.response?.data?.error?.message,
      details: error.response?.data?.error?.details,
      status: error.response?.status,
    };
  }
);
```

### `pdfService.ts`
```typescript
export async function listPDFs(limit = 50, offset = 0) {
  return api.get('/pdf/list', { params: { limit, offset } });
}

export async function getPDFDetails(pdfId: string) {
  return api.get(`/pdf/{pdfId}`);
}

export async function downloadPDF(pdfId: string) {
  return api.get(`/pdf/{pdfId}/download`, { responseType: 'blob' });
}
```

### `parserService.ts`
```typescript
export async function parsePDF(pdfId: string, forceOcr = false) {
  return api.post('/parser/parse', { pdf_id: pdfId, force_ocr: forceOcr });
}

export async function detectPDFType(pdfId: string) {
  return api.post('/parser/detect-type', { pdf_id: pdfId });
}

export async function parseBatch(pdfIds: string[], labels: string[]) {
  return api.post('/parser/parse-batch', { pdf_ids: pdfIds, labels });
}
```

### `comparisonService.ts`
```typescript
export async function compareFDPI(fdId: string, piId: string) {
  return api.post('/comparison/compare-fd-pi', { fd_id: fdId, pi_id: piId });
}

export async function getComparisonHistory(fdId: string, piId: string) {
  return api.get(`/comparison/history/{fdId}/{piId}`);
}
```

### `geminiService.ts`
```typescript
export async function analyzePDF(pdfId: string, query?: string) {
  return api.post('/gemini/analyze', { pdf_id: pdfId, query });
}

export async function checkComponents(pdfId: string) {
  return api.post('/gemini/check-components', { pdf_id: pdfId });
}

export async function summarizePDF(pdfId: string) {
  return api.post('/gemini/summarize', { pdf_id: pdfId });
}

export async function extractInfo(pdfId: string, infoType: string) {
  return api.post('/gemini/extract-info', { pdf_id: pdfId, info_type: infoType });
}
```

---

## 🪝 Custom Hooks

### `usePDFList.ts`
```typescript
export function usePDFList() {
  const [pdfs, setPdfs] = useState<PDFInfo[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPDFs = async (limit = 50, offset = 0) => {
    setIsLoading(true);
    try {
      const result = await listPDFs(limit, offset);
      setPdfs(result.data.pdfs);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return { pdfs, isLoading, error, fetchPDFs };
}
```

### `useComparison.ts`
```typescript
export function useComparison() {
  const [result, setResult] = useState<ComparisonResult | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const compare = async (fdId: string, piId: string) => {
    setIsLoading(true);
    try {
      const result = await compareFDPI(fdId, piId);
      setResult(result.data);
    } catch (err) {
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  return { result, isLoading, error, compare };
}
```

---

## 📝 TypeScript Interfaces

```typescript
// app/src/types/index.ts

export interface PDFInfo {
  id: string;
  filename: string;
  file_size_bytes: number;
  pages: number;
  document_type?: 'FD' | 'PI' | 'OTHER';
  is_scanned?: boolean;
  extraction_method?: string;
  extracted_text_preview?: string;
}

export interface PDFData extends PDFInfo {
  extracted_text?: string;
}

export interface ParseResult {
  text: string;
  page_count: number;
  is_scanned: boolean;
  method: string;
  extraction_time_ms: number;
}

export interface ComparisonResult {
  status: 'CONSISTENT' | 'INCONSISTENT' | 'NEEDS_REVIEW';
  analysis: string;
  processing_time_ms: number;
}

export interface ValidationResult {
  status: 'VALID' | 'INVALID' | 'UNKNOWN';
  math_errors: Array<{
    rule: string;
    expected: string;
    found: string;
    details: string;
  }>;
  structural_errors: Array<{
    section: string;
    issue: string;
    details: string;
  }>;
  missing_components: string[];
  warnings: string[];
}

export interface APIResponse<T> {
  success: boolean;
  data: T | null;
  error: {
    code: string;
    message: string;
    details?: any;
  } | null;
}
```

---

## 🎨 Styling Approach

**Framework:** Tailwind CSS OR Material-UI (choose one)

**Colors:**
- Primary: Blue (#3B82F6)
- Success: Green (#10B981)
- Warning: Yellow (#F59E0B)
- Error: Red (#EF4444)
- Background: White/Light Gray (#F9FAFB)

**Components:**
- Buttons: Primary, Secondary, Outline variants
- Cards: With shadows and borders
- Tables: With hover effects and pagination
- Modals: With backdrop and animations
- Alerts: Error, Success, Info, Warning

---

## 📦 Dependencies to Install

```bash
npm install react react-dom
npm install typescript
npm install axios
npm install tailwindcss postcss autoprefixer
# OR
npm install @mui/material @emotion/react @emotion/styled
npm install @tanstack/react-query  # Optional: for data fetching
npm install zustand               # Optional: for state management
npm install react-router-dom
```

---

## 🚀 Development Workflow

### File Naming Convention
- Components: PascalCase (e.g., `PDFUploader.tsx`)
- Utils/Services: camelCase (e.g., `apiService.ts`)
- Hooks: camelCase with 'use' prefix (e.g., `useComparison.ts`)
- Styles: `.module.css` for component-scoped styles

### Component Structure
```typescript
// PDFViewer.tsx
import { FC, useState, useEffect } from 'react';
import styles from './PDFViewer.module.css';

interface PDFViewerProps {
  pdfId: string;
  onClose: () => void;
}

const PDFViewer: FC<PDFViewerProps> = ({ pdfId, onClose }) => {
  const [state, setState] = useState({});

  useEffect(() => {
    // Load effects
  }, [pdfId]);

  return (
    <div className={styles.container}>
      {/* JSX here */}
    </div>
  );
};

export default PDFViewer;
```

---

## 🔄 Data Flow Diagram

```
User Action
    ↓
Component (React State)
    ↓
Custom Hook (Logic Layer)
    ↓
Service (API Call)
    ↓
Backend Flask API
    ↓
Gemini AI / File System
    ↓
Response JSON
    ↓
Hook (Transform Data)
    ↓
Component (Re-render)
    ↓
Display Result
```

---

## ✨ Key Features to Implement

1. **PDF Upload Interface** 
   - Accept PDFs and add to system
   - Provide instructions for filesystem-based approach

2. **PDF Listing & Management**
   - List all available PDFs
   - Display metadata
   - Quick actions (view, parse, compare, validate)

3. **PDF Parsing**
   - Extract text from PDFs
   - Handle scanned PDFs (OCR detection)
   - Show parsing progress
   - Display extracted text

4. **Document Comparison**
   - Side-by-side view of FD and PI
   - Highlight differences
   - Display inconsistencies
   - Export comparison report

5. **Academic Validation**
   - Check FD for completeness
   - Display math errors
   - Show missing components
   - Recommendations

6. **Error Handling**
   - Display user-friendly error messages
   - Handle API connection issues
   - Retry mechanism for failed requests

7. **Responsive Design**
   - Mobile-friendly
   - Tablet support
   - Desktop optimized

---

## 👁️ Page Layouts

### Home Page
- Welcome message
- Quick action buttons (Upload, Browse, Compare, Validate)
- Recent PDFs
- API status indicator

### PDF Library Page
- Searchable table of PDFs
- Pagination
- Action buttons (View, Parse, Compare, Delete cache, Download)
- File upload area

### Comparison Page
- Dropdown selectors for FD and PI PDFs
- "Start Comparison" button
- Side-by-side text display
- Comparison results panel

### Validation Page
- PDF selector dropdown
- "Run Validation" button
- Results panel with collapsible sections

---

## 📋 Environment Variables (.env)

```
VITE_API_URL=http://localhost:5000/api
VITE_APP_NAME=CodeStorm
VITE_LOG_LEVEL=debug
```

---

## 🧪 Testing Considerations

- Mock API responses for development
- Unit tests for custom hooks
- Integration tests for components
- E2E tests for main workflows

---

**Start building! This comprehensive prompt provides everything needed to create a fully functional Reactor frontend for the CodeStorm system.**

