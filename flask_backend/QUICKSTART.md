# Flask Backend Quick Start Guide

## 5-Minute Setup

### 1. Prerequisites
```bash
# Check Python version (3.9+)
python --version

# Install PostgreSQL
# Windows: https://www.postgresql.org/download/windows/
# Mac: brew install postgresql
# Linux: sudo apt install postgresql
```

### 2. Clone & Navigate
```bash
cd CodeStormProject/flask_backend
```

### 3. Virtual Environment
```bash
# Create
python -m venv venv

# Activate
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate
```

### 4. Install Dependencies
```bash
pip install -r requirements.txt
```

### 5. Environment Setup
```bash
# Copy template
cp .env.example .env

# Edit .env with your values
# GEMINI_API_KEY=your-key-here
# DATABASE_URL=postgresql://postgres:password@localhost:5432/codestorm
```

### 6. Database Setup
```bash
# Create database (if not exists)
createdb codestorm

# Or in psql:
# CREATE DATABASE codestorm;
```

### 7. Run Server
```bash
python run.py
```

Server starts at: `http://localhost:5000`

---

## Testing the API

### Upload PDF
```bash
curl -X POST http://localhost:5000/api/pdf/upload \
  -F "file=@../PDFs/fisa_disciplina.pdf" \
  -F "document_type=FD"
```

### List PDFs
```bash
curl http://localhost:5000/api/pdf/list
```

### Health Check
```bash
curl http://localhost:5000/api/health
```

---

## Common Commands

```bash
# Run server
python run.py

# Run tests
pytest

# Database shell
python

# Activate venv (Windows)
venv\Scripts\activate

# Activate venv (Mac/Linux)
source venv/bin/activate

# Install new package
pip install package-name

# Generate requirements
pip freeze > requirements.txt
```

---

## Environment Variables Reference

```
FLASK_ENV=development              # dev/prod/testing
SECRET_KEY=your-secret-key         # Session secret
DATABASE_URL=postgresql://...      # DB connection
GEMINI_API_KEY=your-key            # Gemini API
UPLOAD_MAX_MB=50                   # Max file size
CORS_ORIGINS=your-frontend-url     # Frontend origin
```

---

## API Endpoints Quick Reference

```
PDF Management:
  POST   /api/pdf/upload           - Upload PDF
  GET    /api/pdf/list             - List PDFs
  GET    /api/pdf/{id}             - Get details
  GET    /api/pdf/{id}/download    - Download
  DELETE /api/pdf/{id}             - Delete

Parsing:
  POST   /api/parser/parse         - Parse single
  POST   /api/parser/detect-type   - Detect type
  POST   /api/parser/parse-batch   - Parse multiple

AI Analysis:
  POST   /api/gemini/analyze       - Analyze
  POST   /api/gemini/check-components - Audit FD
  POST   /api/gemini/summarize     - Summarize
  POST   /api/gemini/extract-info  - Extract info

Comparison:
  POST   /api/comparison/compare-fd-pi - Compare
  GET    /api/comparison/history/{fd_id}/{pi_id}

Editing:
  POST   /api/pdf-edit/extract-layout     - Extract
  POST   /api/pdf-edit/regenerate        - Regenerate
  GET    /api/pdf-edit/{id}/preview      - Preview

System:
  GET    /api/health               - Health check
  GET    /api/health/stats         - Statistics
```

---

## Troubleshooting

### Database Connection Error
```bash
# Test connection
psql -U postgres -d codestorm

# If fails, create DB
createdb codestorm
```

### Gemini API Key Error
- Get key: https://ai.google.dev/
- Set in `.env`: `GEMINI_API_KEY=your-key`
- No spaces around `=`

### Module Not Found
```bash
# Reinstall all dependencies
pip install -r requirements.txt --force-reinstall
```

### Port Already in Use
```bash
# Use different port
python run.py --port 5001

# Or find process on port 5000
# Windows: netstat -ano | findstr :5000
# Mac/Linux: lsof -i :5000
```

---

## Next Steps

1. ✅ **Backend Running** - Server started
2. 📦 **Database Connected** - Tables created
3. 🚀 **Ready for Frontend** - API ready for React app
4. 📝 **See API_ENDPOINTS.md** - Complete endpoint reference

---

## Production Deployment

```bash
# Using Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 wsgi:app

# Using Docker
docker build -t codestorm-backend .
docker run -p 5000:5000 --env-file .env codestorm-backend

# Using Heroku
heroku create codestorm-backend
git push heroku main
heroku config:set FLASK_ENV=production
heroku config:set SECRET_KEY=your-secret
heroku config:set DATABASE_URL=postgresql://...
heroku config:set GEMINI_API_KEY=your-key
```

---

## Support

- **Full Docs:** See `README.md`
- **All Endpoints:** See `API_ENDPOINTS.md`
- **Issues:** Check application logs
- **Database:** Use `psql` for direct queries

---

Happy coding! 🚀

