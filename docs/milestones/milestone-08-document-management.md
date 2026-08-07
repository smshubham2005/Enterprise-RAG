# Milestone 8 - Document Management

> **Phase:** Phase 3 - User Experience
> **Status:** Done

---

## Objective

Add a browser-based document management workflow so users can upload PDFs, see indexed documents, and ask questions without leaving the frontend.

---

## Why

Milestone 7 made the RAG assistant usable for asking questions, but documents still had to be uploaded through backend tooling. Document management closes that loop:

1. **Upload PDFs directly** from the application
2. **Confirm indexing status** before asking questions
3. **Review document coverage** through chunk and page counts
4. **Refresh the knowledge base view** without reloading the app

---

## How

### Document flow

```text
User selects a PDF in React UI
    |
    v
Frontend POSTs multipart form data to /documents/upload
    |
    v
Backend stores, extracts, chunks, embeds, and indexes the PDF
    |
    v
Frontend refreshes GET /documents and shows document metadata
```

### Step-by-step

1. **Document listing API**
   The backend reads ChromaDB chunk metadata and uploaded PDF files, then returns a consolidated document list.

2. **Upload form**
   The frontend sends the selected PDF as multipart form data to `/documents/upload`.

3. **Indexing feedback**
   Upload success displays the filename and chunk count; upload/list failures render visible errors.

4. **Knowledge base shelf**
   The UI shows indexed document count, total chunks, file size, chunk count, and page coverage.

5. **Chat continuity**
   The existing question-and-answer workflow remains on the same screen so the user can upload and immediately ask.

---

## Where

### Files modified

| File | Change |
|------|--------|
| `backend/services/vector_store.py` | Added indexed document aggregation from Chroma metadata |
| `backend/api/document_router.py` | Added `GET /documents` response models and endpoint |
| `frontend/src/App.jsx` | Added document upload, listing, refresh, and status state |
| `frontend/src/App.css` | Added responsive document management styling |
| `docs/milestones/README.md` | Marked Milestone 8 done in the milestone index |

### API endpoints used

| Method | Path | Purpose |
|--------|------|---------|
| GET | `/documents` | List uploaded and indexed PDFs |
| POST | `/documents/upload` | Upload, process, and index a PDF |
| POST | `/ask` | Generate a grounded answer from indexed documents |

---

## How to test

1. Start the backend server on `http://localhost:8000`
2. Start the frontend with `npm run dev` from `frontend/`
3. Open the Vite URL in the browser
4. Upload a PDF using the document form
5. Verify:
   - The upload button shows an indexing state
   - A success message appears with the chunk count
   - The document list refreshes after upload
   - The document card shows indexed status, size, chunks, and pages
   - Asking a question still returns an answer and source cards

---

## What's next

**Milestone 9 - Conversation History:** Persist recent questions and answers in the frontend so users can revisit previous document interactions.
