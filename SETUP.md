# Enterprise RAG - Local Development Setup

## Overview
This project runs locally without Docker during development. Docker will be added as an optional deployment enhancement after the application is complete.

## Prerequisites
- Python 3.11+
- Node.js 18+ with npm
- Git

## Backend Setup

### 1. Navigate to backend directory
```bash
cd backend
```

### 2. Create virtual environment (if not already created)
```bash
python -m venv .venv
```

### 3. Activate virtual environment
**Windows (PowerShell):**
```powershell
.\.venv\Scripts\Activate.ps1
```

**Windows (Command Prompt):**
```cmd
.venv\Scripts\activate.bat
```

**macOS/Linux:**
```bash
source .venv/bin/activate
```

### 4. Install dependencies
```bash
pip install -r requirements.txt
```

### 5. Configure environment variables
Create or update `.env` file in the `backend` directory:
```
GEMINI_API_KEY=your_api_key_here
EMBEDDING_MODEL=models/gemini-embedding-001
GENERATION_MODEL=gemini-flash-latest
GENERATION_TEMPERATURE=0.2
```

### 6. Start the backend server
```bash
uvicorn main:app --reload --port 8000
```

The API will be available at `http://localhost:8000`
API docs: `http://localhost:8000/docs`

---

## Frontend Setup

### 1. Navigate to frontend directory
```bash
cd frontend
```

### 2. Install dependencies
```bash
npm install
```

### 3. Start development server
```bash
npm run dev
```

The frontend will be available at `http://localhost:5173` (or shown in terminal)

---

## Running the Complete Application

**Terminal 1 - Backend:**
```bash
cd backend
.\.venv\Scripts\Activate.ps1  # Windows PowerShell
uvicorn main:app --reload --port 8000
```

**Terminal 2 - Frontend:**
```bash
cd frontend
npm run dev
```

Once both are running:
- Frontend: `http://localhost:5173`
- Backend API: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

---

## Project Structure

```
Enterprise-RAG/
├── backend/
│   ├── .venv/              # Python virtual environment
│   ├── api/                # API routers
│   ├── services/           # Business logic
│   ├── core/               # Configuration
│   ├── main.py             # FastAPI app entry
│   ├── requirements.txt    # Python dependencies
│   └── .env                # Environment variables
│
├── frontend/
│   ├── src/                # React components
│   ├── public/             # Static assets
│   ├── package.json        # npm dependencies
│   └── vite.config.js      # Vite configuration
│
└── docs/                   # Project documentation
    └── milestones/         # Development milestones
```

---

## Development Workflow

1. Make changes to frontend/backend code
2. Changes auto-reload due to `--reload` flag (backend) and Vite HMR (frontend)
3. Check API docs at `http://localhost:8000/docs` for endpoint testing
4. Test frontend at `http://localhost:5173`

---

## Building for Production

**Backend:** No build needed. Deploy the Python code with installed dependencies.

**Frontend:**
```bash
cd frontend
npm run build
```

Output files will be in `frontend/dist/`

---

## Troubleshooting

### Backend port already in use
```bash
uvicorn main:app --reload --port 8001  # Use different port
```

### npm install fails
```bash
npm cache clean --force
npm install
```

### Python dependency issues
```bash
pip install --upgrade pip
pip install --upgrade -r requirements.txt
```

---

## Next Steps
- Refer to `docs/milestones/` for implementation roadmap
- Follow the Enterprise RAG development milestones
- All Docker configuration will be added after project completion
