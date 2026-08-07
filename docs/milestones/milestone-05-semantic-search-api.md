# Milestone 5 — Semantic Search API

> **Phase:** Phase 2 — Retrieval  
> **Status:** Done

---

## Objective

Expose an API that accepts a natural-language query, searches ChromaDB for the most semantically similar document chunks, and returns ranked results with source metadata.

---

## Why

Storing embeddings in ChromaDB (Milestone 4) only helps if we can **retrieve** relevant chunks when a user asks a question. Semantic search is the retrieval half of RAG:

1. **Keyword search fails** on paraphrased questions — "What is our refund policy?" won't match "returns and reimbursements" by exact text
2. **Embeddings capture meaning** — similar questions and answers land close together in vector space
3. **Ranked results** — the LLM in Milestone 6 needs the *best* chunks, not random ones

Without this milestone, we have a database of vectors but no way to query it.

---

## How

### Search flow

```
POST /search  { "query": "What is the refund policy?", "top_k": 4 }
    │
    ▼
Embed the query  (same GoogleGenerativeAIEmbeddings model as ingestion)
    │
    ▼
ChromaDB similarity_search_with_score  →  nearest vectors by L2 distance
    │
    ▼
Return ranked chunks  (content, source_file, page, score)
```

### Step-by-step

1. **Request arrives at `search_router.py`**  
   Validates the query (non-empty) and `top_k` (1–20, default 4).

2. **`semantic_search()` in `vector_store.py`**  
   Reuses the same Chroma collection and embedding model from ingestion — critical so query vectors and document vectors live in the same space.

3. **Empty collection guard**  
   If no documents have been uploaded yet, returns an empty list instead of erroring.

4. **Similarity search**  
   `similarity_search_with_score()` embeds the query, finds the `k` nearest chunks, and returns each with a distance score.

5. **Response mapping**  
   Each result includes the chunk text, source PDF filename, page number, and score for transparency and future citations.

### Key decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Endpoint | `POST /search` | Queries can be long; POST body is cleaner than URL params |
| Default `top_k` | 4 | Enough context for an LLM without overwhelming the prompt (Milestone 6) |
| Score metric | L2 distance (lower = better) | ChromaDB default; documented so consumers interpret scores correctly |
| Separate router | `api/search_router.py` | Search is retrieval logic, distinct from document upload/management |
| Same embedding model | `models/embedding-001` | Query and document vectors must use identical embedding space |

---

## Where

### Files created

| File | Role |
|------|------|
| `backend/api/search_router.py` | Search API endpoint, request/response models |

### Files modified

| File | Change |
|------|--------|
| `backend/services/vector_store.py` | Added `SearchResult` dataclass and `semantic_search()` |
| `backend/core/config.py` | Added `search_top_k` default (4) |
| `backend/main.py` | Registered search router |

### Data / storage

| Location | Read/Write | Purpose |
|----------|------------|---------|
| `backend/chroma_db/` | Read | Queries the persisted vector index |

### API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/search` | Semantic search over ingested chunks |

#### Request body

```json
{
  "query": "What is the refund policy?",
  "top_k": 4
}
```

#### Response body

```json
{
  "query": "What is the refund policy?",
  "result_count": 4,
  "results": [
    {
      "content": "Returns are accepted within 30 days...",
      "source_file": "policy.pdf",
      "page": 5,
      "score": 0.42
    }
  ]
}
```

> **Note:** Lower `score` values mean closer semantic matches (L2 distance).

---

## How to test

1. Ensure at least one PDF has been uploaded (`POST /documents/upload`)
2. Restart the server if needed
3. Open Swagger at `http://localhost:8000/docs`
4. Use **POST /search** with a question related to your uploaded PDF:
   ```json
   {
     "query": "Summarize the main topic of the document",
     "top_k": 3
   }
   ```
5. Verify:
   - `result_count` > 0
   - Each result has `content`, `source_file`, and `page`
   - Results are relevant to your question
6. Test empty state: call `/search` before any upload → `result_count: 0`

---

## What's next

**Milestone 6 — RAG Chain:** Feed these retrieved chunks plus the user's question to Google Gemini to generate a grounded, natural-language answer — completing the full RAG loop.
