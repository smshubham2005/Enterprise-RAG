# Milestone 2 — Backend Foundation & PDF Upload API

> **Phase:** Phase 1 — Ingestion  
> **Status:** Done

---

## Objective

Stand up the FastAPI backend with CORS, health checks, and a PDF upload endpoint that saves files to disk — the entry point for the entire ingestion pipeline.

---

## Why

Before we can extract text or build a vector store, we need a reliable way to:

1. **Accept documents** from the frontend (or Swagger during development)
2. **Validate** that only PDFs are uploaded
3. **Persist files locally** so later milestones can read and process them

Without this layer, there is no file on the server for LangChain to load. Every downstream milestone (chunking, embedding, ChromaDB, search) depends on a saved PDF path.

---

## How

### Request flow

```
Client (Swagger / Frontend)
    │
    ▼
POST /documents/upload  (multipart form, PDF file)
    │
    ▼
Validate extension == .pdf
    │
    ▼
Stream file to disk  (backend/uploads/<filename>)
    │
    ▼
Return UploadResponse  (filename, size, message)
```

### Implementation details

1. **`main.py`** creates the FastAPI app, enables CORS for the Vite dev server (`localhost:5173`), and mounts the document router.
2. **`document_router.py`** defines the `/documents` prefix and handles upload logic.
3. Files are written with `shutil.copyfileobj` — streaming piece-by-piece instead of loading the whole PDF into memory (important for large documents).
4. On failure, any partially written file is deleted so we don't leave corrupted uploads on disk.

### Key decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| File format | PDF only | Standard enterprise document format; PyPDFLoader supports it in Milestone 3 |
| Upload directory | `backend/uploads/` | Colocated with backend code; gitignored for actual PDFs |
| CORS origin | `http://localhost:5173` | Matches Vite's default dev port for the React frontend |

---

## Where

### Files created

| File | Role |
|------|------|
| `backend/main.py` | FastAPI app entry point, CORS, router registration |
| `backend/api/__init__.py` | Makes `api` a Python package |
| `backend/api/document_router.py` | Upload endpoint and response models |
| `backend/uploads/.gitkeep` | Keeps the uploads folder in git without committing PDFs |

### Files modified

| File | Change |
|------|--------|
| `.gitignore` | Ignores `backend/uploads/*.pdf` and `.env` |

### Data / storage

| Location | Contents |
|----------|----------|
| `backend/uploads/` | Uploaded PDF files (temporary until ingestion) |

### API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/` | Welcome message |
| GET | `/health` | Health check for monitoring |
| POST | `/documents/upload` | Upload a PDF file |

---

## How to test

1. Start the server:
   ```powershell
   cd backend
   .venv\Scripts\activate
   python -m uvicorn main:app --reload
   ```
2. Open `http://localhost:8000/docs`
3. Use **POST /documents/upload** → choose a PDF → Execute
4. Confirm the response shows `filename`, `size_bytes`, and success message
5. Verify the file exists in `backend/uploads/`

---

## What's next

**Milestone 3 — Text Extraction, Chunking & Embeddings:** Once a PDF is on disk, we read its text, split it into searchable chunks, and convert them into vector embeddings using Google Gemini.
