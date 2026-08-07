# Milestone 7 - Basic Frontend Chat Interface

> **Phase:** Phase 3 - User Experience  
> **Status:** Done

---

## Objective

Replace the starter Vite screen with a practical React chat interface that sends user questions to the backend `/ask` endpoint and displays grounded answers with source snippets.

---

## Why

Milestone 6 completes the backend RAG loop, but users still need Swagger or raw HTTP calls to use it. A frontend chat interface makes the assistant usable:

1. **Ask questions naturally** from the browser
2. **See generated answers** without inspecting JSON manually
3. **Review sources** so answers remain traceable to uploaded documents

Without this milestone, the product works technically but does not yet feel like an assistant.

---

## How

### Chat flow

```text
User enters question in React UI
    |
    v
Frontend POSTs { query, top_k } to /ask
    |
    v
Backend retrieves chunks and generates an answer
    |
    v
Frontend renders answer, source count, source cards, and errors
```

### Step-by-step

1. **Question input**  
   The user types a question and selects how many chunks to use as context.

2. **Request dispatch**  
   `App.jsx` sends a `POST` request to `${VITE_API_BASE_URL || http://localhost:8000}/ask`.

3. **Loading and error states**  
   The submit button disables while waiting, and API failures appear in a visible error panel.

4. **Answer rendering**  
   Successful responses show the natural-language answer and how many source chunks were used.

5. **Source review**  
   Each returned source displays filename, page, score, and chunk content.

### Key decisions

| Decision | Choice | Reason |
|----------|--------|--------|
| API base URL | `VITE_API_BASE_URL` fallback | Works locally while allowing environment-specific backend URLs |
| First screen | Chat workspace | Milestone 7 is a usable app surface, not a landing page |
| Sources visible | Source cards below answer | Keeps RAG answers auditable for enterprise use |
| Examples | Quick question chips | Makes manual testing faster after upload |
| Styling | Plain CSS | Matches current Vite setup without adding dependencies |

---

## Where

### Files modified

| File | Change |
|------|--------|
| `frontend/src/App.jsx` | Replaced starter screen with RAG chat workflow |
| `frontend/src/App.css` | Added responsive app layout and chat/source styling |
| `frontend/src/index.css` | Simplified global base styles |
| `docs/milestones/README.md` | Marked Milestone 7 done and added execution review guidance |

### API endpoints used

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/ask` | Generate a grounded answer from uploaded documents |

---

## How to test

1. Start the backend server on `http://localhost:8000`
2. Upload at least one PDF through Swagger or the document upload API
3. Start the frontend with `npm run dev` from `frontend/`
4. Open the Vite URL in the browser
5. Ask a question about the uploaded PDF
6. Verify:
   - Loading state appears while waiting
   - Answer appears after the request completes
   - Source cards show filename, page, score, and content
   - Invalid backend/API states render an error message

---

## What's next

**Milestone 8 - Document Management:** Add a frontend upload and document list workflow so users can manage PDFs without leaving the app.
