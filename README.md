# PDF Import UI with Chainlit

A user-friendly Chainlit-based application for importing and processing 2 PDF documents.

## Features

- **PDF Upload**: Easy file upload interface for importing up to 2 PDF documents
- **File Validation**: Automatic validation to ensure only PDF files are accepted
- **Document Preview**: Displays page count and text preview from the first page
- **Session Management**: Stores uploaded documents in the session for processing
- **User Feedback**: Real-time feedback on upload status and document information

## Installation

1. **Clone or download the project**

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the application**:
   ```bash
   chainlit run main.py
   ```

The application will start on `http://localhost:8000` by default.

## Usage

1. Open the application in your web browser
2. Click the file upload button or drag and drop PDF files
3. Upload up to 2 PDF documents
4. The application will:
   - Validate the files
   - Extract metadata (page count, preview text)
   - Display a summary of all imported documents

## File Structure

- `main.py` - Entry point for the application
- `UI.py` - Chainlit UI implementation with PDF handling logic
- `requirements.txt` - Python package dependencies

## API Functions

### `get_loaded_pdfs()`
Returns a list of loaded PDF documents with their metadata:
```python
[
    {
        'name': 'document.pdf',
        'path': '/path/to/document.pdf',
        'pages': 10,
        'preview': 'First 200 characters of text...'
    }
]
```

### `clear_pdfs()`
Clears all loaded PDF documents from memory.

## Requirements

- Python 3.8+
- chainlit
- PyPDF2

## Notes

- Maximum of 2 PDF documents can be imported at once
- Only PDF files are accepted
- The preview text shows the first 200 characters from the first page

