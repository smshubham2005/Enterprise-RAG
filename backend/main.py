from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.ask_router import router as ask_router
from api.document_router import router as document_router
from api.search_router import router as search_router
from api.auth_router import router as auth_router

app = FastAPI(
    title="Enterprise RAG Assistant API",
    description="Backend API for the RAG Assistant",
    version="1.0.0"
)

from core.config import get_settings

settings = get_settings()
parsed_origins = [origin.strip() for origin in settings.allowed_origins.split(",") if origin.strip()]

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=parsed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include Routers
app.include_router(auth_router)
app.include_router(document_router)
app.include_router(search_router)
app.include_router(ask_router)

@app.get("/")
async def root():
    return {"message": "Welcome to the Enterprise RAG Assistant API"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}





