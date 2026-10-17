import os
from pathlib import Path
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field

class Settings(BaseSettings):
    gemini_api_key: str = Field(..., alias="GEMINI_API_KEY")

    # Model configuration
    embedding_model: str = "models/embedding-001"
    generation_model: str = "gemini-1.5-flash"
    generation_temperature: float = 0.0

    # JWT Authentication configuration
    jwt_secret_key: str = Field(..., alias="JWT_SECRET_KEY")
    jwt_algorithm: str = "HS256"
    jwt_expiration_minutes: int = Field(60, alias="JWT_EXPIRATION_MINUTES")
    admin_password_hash: str = Field(..., alias="ADMIN_PASSWORD_HASH")
    admin_plain_password: Optional[str] = Field(None, alias="ADMIN_PASSWORD_PLAIN")

    # Upload Validation configuration
    max_upload_size_mb: int = Field(10, alias="MAX_UPLOAD_SIZE_MB")
    max_pdf_pages: int = Field(200, alias="MAX_PDF_PAGES")
    max_extracted_text_chars: int = Field(2_000_000, alias="MAX_EXTRACTED_TEXT_CHARS")

    # Pinecone (persistent cloud vector store)
    pinecone_api_key: str = Field(..., alias="PINECONE_API_KEY")
    pinecone_index_name: str = Field("enterprise-rag", alias="PINECONE_INDEX_NAME")

    # Upload directory (temp — files deleted after indexing)
    base_dir: Path = Path(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    upload_dir: Path = base_dir / "uploads"

    # Retrieval configuration
    search_top_k: int = 4
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # CORS Configuration
    allowed_origins: str = Field(
        "http://localhost,http://localhost:80,http://127.0.0.1,http://127.0.0.1:80,http://localhost:5173,http://127.0.0.1:5173",
        alias="ALLOWED_ORIGINS"
    )

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )

@lru_cache
def get_settings() -> Settings:
    """Returns a cached instance of the Settings."""
    return Settings()
