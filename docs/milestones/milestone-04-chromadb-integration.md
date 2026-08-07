# Milestone 4 — Vector Storage (ChromaDB Integration)

> **Phase:** Phase 1 — Ingestion  
> **Status:** Done

---

## Objective

Persist document chunks and their embeddings in ChromaDB so they survive server restarts and can be searched semantically in the next phase.

---

## Why

Milestone 3 generates embeddings in memory during upload, but without storage they are lost when the request finishes. ChromaDB solves this by:

1. **Persisting vectors to disk** — data survives restarts (`backend/chroma_db/`)
2. **Indexing for similarity search** — optimized lookup by vector distance (used in Milestone 5)
3. **Storing metadata alongside vectors** — filename, page number, etc. for citations later

ChromaDB was chosen because it runs embedded in Python (no separate server), persists locally, and integrates cleanly with LangChain — ideal for development and production-capable for early deployment.

---

## How

### Storage flow

```
Chunks from rag_service (with page metadata)
    │
    ▼
Add source_file metadata to each chunk
    │
    ▼
Chroma.add_documents(chunks)
    │
    ├── Embeds each chunk via GoogleGenerativeAIEmbeddings
    └── Writes vectors + metadata to backend/chroma_db/
    │
    ▼
Returns stored count → API response
```

### Step-by-step

1. **Vector store service (`services/vector_store.py`)**  
   New dedicated module for all ChromaDB operations — separate from extraction/chunking logic.

2. **`get_embeddings()`**  
   Cached singleton (`@lru_cache`) so we reuse one embedding model instance across requests instead of creating a new client every time.

3. **`get_vector_store()`**  
   Opens (or creates) a Chroma collection named `enterprise_rag` at `backend/chroma_db/`. LangChain handles embedding automatically when documents are added.

4. **`store_documents()`**  
   Tags each chunk with `source_file` metadata (the PDF filename), then calls `vectorstore.add_documents()`. ChromaDB assigns IDs and persists everything.

5. **Refactored `rag_service.py`**  
   Now delegates storage to `vector_store.store_documents()` instead of manually calling `embed_documents()`. Extraction and chunking stay here; storage is vector_store's job.

6. **Stats endpoint (`GET /documents/stats`)**  
   Lets you verify how many chunks are in the collection without uploading again.

### Key decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Vector DB | ChromaDB | Lightweight, local persistence, native LangChain support |
| Persist directory | `backend/chroma_db/` | On-disk storage; gitignored except `.gitkeep` |
| Collection name | `enterprise_rag` | Single collection for all documents (multi-doc management comes in Milestone 8) |
| Metadata | `source_file` + existing `page` | Enables source citations in Milestone 10 |
| Separate service file | `vector_store.py` | Clear separation: rag_service = process, vector_store = persist/query |

---

## Where

### Files created

| File | Role |
|------|------|
| `backend/services/vector_store.py` | ChromaDB client, embedding singleton, store & stats functions |
| `backend/chroma_db/.gitkeep` | Keeps persist directory in git without committing DB files |

### Files modified

| File | Change |
|------|--------|
| `backend/core/config.py` | Added `chroma_persist_dir`, `chroma_collection_name` |
| `backend/services/rag_service.py` | Calls `store_documents()` instead of manual embedding |
| `backend/api/document_router.py` | Added `GET /documents/stats`; response includes `collection_name` |
| `.gitignore` | Ignores `backend/chroma_db/` contents |

### Data / storage

| Location | Contents |
|----------|----------|
| `backend/chroma_db/` | ChromaDB persist files (vectors, metadata, index) |
| `backend/uploads/` | Original PDF files (unchanged from Milestone 2) |

Each stored chunk carries metadata like:
```json
{
  "source_file": "report.pdf",
  "page": 3
}
```

### API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/documents/upload` | Upload → extract → chunk → embed → **store in ChromaDB** |
| GET | `/documents/stats` | **New** — returns collection name, chunk count, persist path |

---

## How to test

1. Restart the server (ensure `.env` has `GEMINI_API_KEY`)
2. Upload a PDF via Swagger: **POST /documents/upload**
   ```json
   {
     "filename": "report.pdf",
     "message": "File uploaded, processed, and stored in ChromaDB",
     "chunk_count": 42,
     "embedding_count": 42,
     "embedding_dimensions": 768,
     "collection_name": "enterprise_rag"
   }
   ```
3. Check storage: **GET /documents/stats**
   ```json
   {
     "collection_name": "enterprise_rag",
     "chunk_count": 42,
     "persist_directory": "D:\\self\\Enterprise-RAG\\backend\\chroma_db"
   }
   ```
4. Restart the server again and call `/documents/stats` — chunk count should **persist** (proving disk storage works)
5. Upload a second PDF — chunk count should **increase**

---

## What's next

**Milestone 5 — Semantic Search API:** Query the ChromaDB collection with a natural-language question, retrieve the most similar chunks, and return them as ranked results — the retrieval half of RAG.
