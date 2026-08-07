# Enterprise RAG Assistant

A production-quality Retrieval-Augmented Generation (RAG) assistant built from scratch to allow users to securely upload multiple PDF documents and perform context-grounded conversational search.

## 🚀 Key Features

*   **Secure Multi-PDF Ingestion**: Processes files page-by-page, dynamically chunking texts using `RecursiveCharacterTextSplitter`.
*   **Vector Database Storage**: Indexes and queries document embeddings persistently using `ChromaDB` (via `langchain-chroma`).
*   **Conversational History & Pronoun Resolution**: Remembers context from previous dialogue turns. Uses query condensation (LLM rephrasing) to resolve references in follow-up queries.
*   **Inline Source Citations**: Presents grounded reference links detailing document source, page number, match distance score, and extracted context snippets.
*   **Mock Authentication Layer**: Restricts backend uploads and queries behind a bearer token validation schema, supporting logout and multi-user simulation.
*   **High-Aesthetic UI**: Modern, responsive interface with dual-pane layout, animated indicators, and a citations details drawer.

---

## 🛠️ Technology Stack

### Backend
*   **FastAPI**: Asynchronous Python API gateway.
*   **LangChain**: Ingestion loader pipeline and prompt templates orchestration.
*   **ChromaDB**: Native AI vector store database.
*   **Google Gemini API**: Embeddings (`models/embedding-001`) and generation (`gemini-1.5-flash`).
*   **Pydantic Settings**: Centralized configuration management.

### Frontend
*   **React (Vite)**: Component-driven single page application.
*   **Tailwind CSS (v4)**: Modern, custom utility-first presentation styles.
*   **Axios / Fetch**: Client-to-server communication.

---

## 📁 Project Structure

```text
Enterprise-RAG/
├── backend/
│   ├── api/                  # FastAPI routers (documents, ask, auth)
│   ├── core/                 # Settings config and logger configurations
│   ├── services/             # Core business logic (RAG pipeline, vector store, QA)
│   ├── uploads/              # Temporary file system storage (git ignored)
│   ├── logs/                 # Persistent runtime logger dumps (git ignored)
│   ├── main.py               # Entry API startup script
│   └── requirements.txt      # Python dependencies manifest
├── frontend/
│   ├── src/
│   │   ├── App.jsx           # Main React component & state logic
│   │   ├── App.css           # Custom Tailwind and conversational UI styles
│   │   └── main.jsx          # Entry point
│   ├── package.json          # Node dependencies manifest
│   └── vite.config.js        # Vite bundler options
└── README.md                 # Project handbook
```

---

## ⚙️ Installation & Running

### Prerequisites
*   Python 3.11+
*   Node.js 18+
*   Google Gemini API Key (obtained from [Google AI Studio](https://aistudio.google.com/))

### 1. Backend Setup
Navigate to the `backend` folder:
```bash
cd backend
python -m venv .venv
```
Activate the virtual environment:
*   **Windows (PowerShell)**: `.\.venv\Scripts\activate`
*   **Mac/Linux**: `source .venv/bin/activate`

Install dependencies:
```bash
pip install -r requirements.txt
```

Create a `.env` file in the `backend` directory (use `.env.example` as a template):
```env
GEMINI_API_KEY=your_actual_gemini_api_key
```

Run the server:
```bash
uvicorn main:app --reload
```
The backend API will run on `http://localhost:8000`. You can inspect endpoints via `http://localhost:8000/docs`.

### 2. Frontend Setup
Navigate to the `frontend` folder:
```bash
cd frontend
npm install
```

Start the local server:
```bash
npm run dev
```
Open `http://localhost:5173/` in your browser.

---

## 🔒 Default Login Credentials (Mock)
*   **Username**: `admin` (or any string)
*   **Password**: `admin123`

---

## 🧠 Technical Interview Q&A (RAG Insights)

### Q: Why do you perform "Query Condensation" in a conversational RAG system?
> **Answer**: In multi-turn chat, users frequently ask follow-up questions containing pronouns (e.g. *"How is it calculated?"*). If we search the vector database directly with *"How is it calculated?"*, the search will fail because "it" has no semantic definition. Query condensation takes the chat history and follow-up query and prompts the LLM to rewrite it into a self-contained search query (e.g. *"How is Gross Domestic Product calculated?"*) before performing the database lookup.

### Q: Explain the trade-offs of using `RecursiveCharacterTextSplitter`.
> **Answer**: This splitter recursively attempts to split text using a prioritized list of separators (`["\n\n", "\n", " ", ""]`). This keeps logical semantic structures (like paragraphs and sentences) together, yielding high retrieval quality. This contrasts with `CharacterTextSplitter` (which splits strictly on a single delimiter and can create uneven chunks) and `TokenTextSplitter` (which splits on hard token limits, often cutting words/sentences in half and degrading retrieval accuracy).

### Q: How does your application prevent Out-Of-Memory (OOM) errors during file uploads?
> **Answer**: Rather than reading the entire PDF payload directly into RAM memory, the FastAPI upload router streams the incoming `multipart/form-data` payload in chunks using `shutil.copyfileobj` onto a local temporary disk storage (`uploads/`). The file is then parsed and chunked iteratively before we clean up temporary assets.
