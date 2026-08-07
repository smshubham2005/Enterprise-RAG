# Milestone Documentation

Each milestone has its own explanation file covering **what**, **why**, **how**, and **where** — so you can understand not just what was built, but the reasoning and file layout behind it.

## Index

| Milestone | Title | Status | Doc |
|-----------|-------|--------|-----|
| 1 | Project Planning & Environment Setup | Done | *(planning only — no code doc)* |
| 2 | Backend Foundation & PDF Upload API | Done | [milestone-02](./milestone-02-backend-foundation.md) |
| 3 | Text Extraction, Chunking & Embeddings | Done | [milestone-03](./milestone-03-text-extraction-chunking-embeddings.md) |
| 4 | Vector Storage (ChromaDB Integration) | Done | [milestone-04](./milestone-04-chromadb-integration.md) |
| 5 | Semantic Search API | Done | [milestone-05](./milestone-05-semantic-search-api.md) |
| 6 | RAG Chain (Gemini) | Done | [milestone-06](./milestone-06-rag-chain.md) |
| 7 | Basic Frontend Chat Interface | Done | [milestone-07](./milestone-07-frontend-chat-interface.md) |
| 8 | Document Management | Done | [milestone-08](./milestone-08-document-management.md) |

## Doc structure

Every milestone file follows the same sections:

1. **Objective** — what this milestone delivers
2. **Why** — why we need it in the RAG pipeline
3. **How** — step-by-step execution logic
4. **Where** — files, folders, and API endpoints touched
5. **How to test** — commands or Swagger steps to verify
6. **What's next** — which milestone builds on this one

Use [`_template.md`](./_template.md) when adding docs for future milestones.


## Reviewing milestone execution

Use the milestone docs for the implementation narrative, then verify behavior through the running app/API:

1. **Read the doc** - each milestone file explains objective, flow, files touched, endpoints, and test steps.
2. **Inspect code changes** - use `git diff` or `git status --short` to see the exact files changed.
3. **Exercise backend endpoints** - open `http://localhost:8000/docs` and run upload, search, and ask flows.
4. **Run focused checks** - use Python compile checks for backend files and `npm run build` for frontend changes.
5. **Review the UI** - start Vite and confirm the frontend calls the expected backend API.


