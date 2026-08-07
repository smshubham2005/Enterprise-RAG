# Milestone 3 — Text Extraction, Chunking & Embeddings

> **Phase:** Phase 1 — Ingestion  
> **Status:** Done

---

## Objective

After a PDF is uploaded, extract its text, split it into semantic chunks, and generate vector embeddings using Google Gemini — preparing raw documents for AI-powered search.

---

## Why

LLMs and vector databases cannot meaningfully search an entire 50-page PDF as one block. We need to:

1. **Extract text** — PDFs are binary; we need plain text LangChain can work with
2. **Chunk text** — smaller pieces improve search precision and stay within token limits
3. **Embed chunks** — convert text into numerical vectors so we can measure semantic similarity later

This is the core "understanding" step of RAG. Without chunks and embeddings, Milestone 4 (ChromaDB) and Milestone 5 (semantic search) have nothing to store or query.

---

## How

### Processing pipeline

```
PDF on disk (backend/uploads/report.pdf)
    │
    ▼
PyPDFLoader.load()          →  List of Documents (one per page)
    │
    ▼
RecursiveCharacterTextSplitter  →  ~1000-char chunks with 200-char overlap
    │
    ▼
GoogleGenerativeAIEmbeddings    →  Vector for each chunk (768 dimensions)
    │
    ▼
ProcessResult returned to API
```

### Step-by-step

1. **Configuration (`core/config.py`)**  
   Uses `pydantic-settings` to load secrets and tunables from `backend/.env`:
   - `GEMINI_API_KEY` — required for Gemini API calls
   - `chunk_size=1000`, `chunk_overlap=200` — chunking defaults

2. **Service layer (`services/rag_service.py`)**  
   Isolates LangChain logic from the HTTP router. The router should not know about PDF loaders or splitters — only call `process_document()`.

3. **Text extraction**  
   `PyPDFLoader` reads each page and returns LangChain `Document` objects with `page_content` and metadata (e.g. page number).

4. **Chunking**  
   `RecursiveCharacterTextSplitter` tries to split on natural boundaries (paragraphs → sentences → words) rather than cutting mid-word. Overlap ensures context isn't lost at chunk boundaries.

5. **Embeddings**  
   `GoogleGenerativeAIEmbeddings` (model: `models/embedding-001`) sends chunk text to Gemini and receives a 768-dimensional vector representing its meaning.

6. **Router integration**  
   After saving the PDF, `document_router.py` calls `process_document()` and returns chunk/embedding stats in the response.

### Key decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Chunk size | 1000 characters | Industry-standard balance: enough context per chunk, not so large that search becomes imprecise |
| Chunk overlap | 200 characters | Preserves continuity across chunk boundaries (e.g. a sentence split across two chunks) |
| Embedding model | `models/embedding-001` | Google's stable embedding model; 768 dimensions |
| Config library | `pydantic-settings` | Type-safe env loading; fails fast if `GEMINI_API_KEY` is missing |
| Service pattern | `services/rag_service.py` | Keeps routers thin; business logic is testable and reusable |

---

## Where

### Files created

| File | Role |
|------|------|
| `backend/core/config.py` | Centralized settings (API key, chunk params, embedding model) |
| `backend/core/__init__.py` | Package marker |
| `backend/services/rag_service.py` | PDF → chunks → embeddings pipeline |
| `backend/services/__init__.py` | Package marker |
| `backend/.env.example` | Template for required environment variables |

### Files modified

| File | Change |
|------|--------|
| `backend/api/document_router.py` | Calls `process_document()` after upload; extended response with chunk/embedding stats |
| `backend/requirements.txt` | Added `langchain-community`, `langchain-text-splitters` |

### Configuration

| Variable | Location | Purpose |
|----------|----------|---------|
| `GEMINI_API_KEY` | `backend/.env` | Authenticates Gemini embedding API calls |

### API endpoints

| Method | Path | Change |
|--------|------|--------|
| POST | `/documents/upload` | Now processes PDF after save; returns `chunk_count`, `embedding_count`, `embedding_dimensions` |

---

## How to test

1. Create `backend/.env` from the example and add your Gemini API key:
   ```powershell
   copy .env.example .env
   ```
2. Install deps in your venv (if not already):
   ```powershell
   .venv\Scripts\python.exe -m pip install -r requirements.txt
   ```
3. Restart the server and upload a PDF via Swagger (`POST /documents/upload`)
4. Expected response fields:
   - `chunk_count` > 0
   - `embedding_count` matches `chunk_count`
   - `embedding_dimensions` ≈ 768

---

## What's next

**Milestone 4 — ChromaDB Integration:** Embeddings are generated but ephemeral unless stored. ChromaDB persists chunks + vectors to disk so we can search them in Milestone 5.
