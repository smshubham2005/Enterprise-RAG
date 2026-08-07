import os
import shutil
import uuid
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from pydantic import BaseModel

from services.rag_service import process_document
from services.pdf_validator import validate_pdf_upload
from services.vector_store import (
    get_collection_stats,
    list_indexed_documents,
    delete_document,
)
from api.auth_router import verify_token
from core.config import get_settings

router = APIRouter(
    prefix="/documents",
    tags=["Documents"]
)

UPLOAD_DIR = Path(os.path.dirname(os.path.dirname(__file__))) / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
RESOLVED_UPLOAD_DIR = UPLOAD_DIR.resolve()


class UploadResponse(BaseModel):
    filename: str
    message: str
    size_bytes: int
    chunk_count: int
    embedding_count: int
    embedding_dimensions: int
    collection_name: str


class CollectionStatsResponse(BaseModel):
    collection_name: str
    chunk_count: int
    persist_directory: str


class DocumentListItem(BaseModel):
    id: str
    filename: str
    size_bytes: int | None
    chunk_count: int
    pages: list[int]
    indexed: bool


class DocumentListResponse(BaseModel):
    total_documents: int
    total_chunks: int
    documents: list[DocumentListItem]


@router.get("", response_model=DocumentListResponse)
async def list_documents(username: str = Depends(verify_token)):
    """Return uploaded and indexed PDF documents."""
    try:
        indexed_documents = list_indexed_documents()
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(error)}"
        )

    document_list = []
    for document in indexed_documents:
        file_path = (UPLOAD_DIR / document.storage_filename).resolve()
        size_bytes = None
        
        # Verify safety and check size if file exists on disk
        if file_path.is_relative_to(RESOLVED_UPLOAD_DIR) and file_path.exists():
            size_bytes = file_path.stat().st_size

        document_list.append(
            DocumentListItem(
                id=document.document_id,
                filename=document.source_file,
                size_bytes=size_bytes,
                chunk_count=document.chunk_count,
                pages=document.pages,
                indexed=True,
            )
        )

    document_list.sort(key=lambda doc: doc.filename.lower())

    return DocumentListResponse(
        total_documents=len(document_list),
        total_chunks=sum(document.chunk_count for document in document_list),
        documents=document_list,
    )


@router.get("/stats", response_model=CollectionStatsResponse)
async def document_stats(username: str = Depends(verify_token)):
    """Return ChromaDB collection statistics."""
    return get_collection_stats()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    username: str = Depends(verify_token)
):
    """
    Upload a PDF document, extract text, chunk it, embed it, and store in ChromaDB.
    File is stored securely on disk using a UUID filename after pre-write validation.
    """
    settings = get_settings()

    # Pre-write validation (extension, MIME, magic bytes, size, encryption, pages, text limit)
    validate_pdf_upload(file, settings)

    document_id = str(uuid.uuid4())
    storage_filename = f"{document_id}.pdf"
    file_path = (UPLOAD_DIR / storage_filename).resolve()

    # Path traversal validation check
    if not file_path.is_relative_to(RESOLVED_UPLOAD_DIR):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename or path traversal attempt detected."
        )

    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = file_path.stat().st_size

        result = process_document(
            str(file_path),
            file.filename,
            document_id=document_id,
            storage_filename=storage_filename
        )

        return UploadResponse(
            filename=file.filename,
            message="File uploaded, processed, and stored in ChromaDB",
            size_bytes=file_size,
            chunk_count=result.chunk_count,
            embedding_count=result.embedding_count,
            embedding_dimensions=result.embedding_dimensions,
            collection_name=result.collection_name,
        )

    except Exception as e:
        if file_path.exists():
            file_path.unlink()

        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {str(e)}"
        )


# ==========================================================
# DELETE DOCUMENT FROM CHROMADB BY DOCUMENT_ID
# ==========================================================

@router.delete("/{document_id}")
async def delete_uploaded_document(
    document_id: str,
    username: str = Depends(verify_token)
):
    """
    Delete a document from ChromaDB by document_id and
    remove its corresponding storage file from disk.
    """

    try:
        # Delete vectors from ChromaDB and get storage_filename
        storage_filename = delete_document(document_id)

        if not storage_filename:
            raise HTTPException(
                status_code=404,
                detail="Document not found."
            )

        file_path = (UPLOAD_DIR / storage_filename).resolve()

        # Path traversal security verification
        if file_path.is_relative_to(RESOLVED_UPLOAD_DIR) and file_path.exists():
            file_path.unlink()

        return {
            "success": True,
            "message": "Document deleted successfully."
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to delete document: {str(e)}"
        )