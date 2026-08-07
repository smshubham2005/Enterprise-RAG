# Milestone 6 - RAG Chain

> **Phase:** Phase 2 - Retrieval  
> **Status:** Done

---

## Objective

Add a question-answering API that retrieves relevant ChromaDB chunks, sends them to Google Gemini with the user's question, and returns a grounded natural-language answer with source snippets.

---

## Why

Milestone 5 can find relevant passages, but users still have to read and synthesize those chunks themselves. A RAG chain completes the core loop:

1. **Retrieve** the best document chunks for the question
2. **Augment** the prompt with those chunks as context
3. **Generate** a concise answer that stays grounded in uploaded documents

Without this milestone, the system is a semantic search API rather than an assistant.

---

## How

### Answer flow

```text
POST /ask  { "query": "What is the refund policy?", "top_k": 4 }
    |
    v
semantic_search() retrieves relevant chunks from ChromaDB
    |
    v
qa_service builds a grounded prompt with source labels
    |
    v
Gemini generates an answer using only retrieved context
    |
    v
Return answer plus source snippets
```

### Step-by-step

1. **Request arrives at `ask_router.py`**  
   Validates the question and context size.

2. **`answer_question()` retrieves context**  
   Reuses `semantic_search()` so generation and search share the same retrieval behavior.

3. **Empty collection guard**  
   If no chunks are available, returns a clear no-context answer without calling the LLM.

4. **Grounded prompt construction**  
   Each chunk is labeled as `Source 1`, `Source 2`, and so on, with filename, page, and score metadata.

5. **Gemini answer generation**  
   `ChatGoogleGenerativeAI` receives the question and context, then returns a concise answer with inline source labels.

### Key decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| Endpoint | `POST /ask` | Separates answer generation from raw semantic search |
| Retrieval reuse | `semantic_search()` | Keeps ranking behavior consistent with Milestone 5 |
| Source labels | `[Source 1]` style | Makes answers traceable without requiring frontend citation logic yet |
| Empty state | No LLM call | Avoids spending tokens when there is no document context |
| Model config | `GENERATION_MODEL` | Lets the generation model change without code edits |

---

## Where

### Files created

| File | Role |
|------|------|
| `backend/api/ask_router.py` | RAG answer endpoint and response models |
| `backend/services/qa_service.py` | Retrieval + prompt construction + Gemini generation |
| `docs/milestones/milestone-06-rag-chain.md` | Milestone documentation |

### Files modified

| File | Change |
|------|--------|
| `backend/main.py` | Registered the ask router |
| `backend/core/config.py` | Added generation model and temperature settings |
| `backend/.env.example` | Documented generation environment variables |
| `docs/milestones/README.md` | Marked Milestone 6 as done |

### Data / storage

| Location | Read/Write | Purpose |
|----------|------------|---------|
| `backend/chroma_db/` | Read | Retrieves persisted document chunks for answer context |

### API endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/ask` | Generate a grounded answer from uploaded documents |

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
  "answer": "Returns are accepted within 30 days [Source 1].",
  "source_count": 4,
  "sources": [
    {
      "content": "Returns are accepted within 30 days...",
      "source_file": "policy.pdf",
      "page": 5,
      "score": 0.42
    }
  ]
}
```

---

## How to test

1. Ensure `backend/.env` contains a valid `GEMINI_API_KEY`
2. Start the backend server
3. Upload at least one PDF using `POST /documents/upload`
4. Open Swagger at `http://localhost:8000/docs`
5. Use **POST /ask** with a question related to the uploaded PDF:
   ```json
   {
     "query": "Summarize the main topic of the document",
     "top_k": 4
   }
   ```
6. Verify:
   - `answer` is natural language
   - `sources` contains the retrieved chunks
   - The answer includes source labels such as `[Source 1]`
7. Test empty state: call `/ask` before any upload and confirm it returns a no-context answer.

---

## What's next

**Milestone 7 - Basic Frontend Chat Interface:** Build a React UI that calls `/ask`, displays answers, and shows source snippets to the user.
