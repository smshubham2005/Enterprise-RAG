import asyncio
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
    """Return all indexed PDF documents from Pinecone metadata."""
    try:
        indexed_documents = list_indexed_documents()
    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to list documents: {str(error)}"
        )

    document_list = [
        DocumentListItem(
            id=document.document_id,
            filename=document.source_file,
            size_bytes=document.size_bytes,  # stored in Pinecone metadata
            chunk_count=document.chunk_count,
            pages=document.pages,
            indexed=True,
        )
        for document in indexed_documents
    ]

    document_list.sort(key=lambda doc: doc.filename.lower())

    return DocumentListResponse(
        total_documents=len(document_list),
        total_chunks=sum(doc.chunk_count for doc in document_list),
        documents=document_list,
    )


@router.get("/stats", response_model=CollectionStatsResponse)
async def document_stats(username: str = Depends(verify_token)):
    """Return Pinecone index statistics."""
    return get_collection_stats()


@router.post("/upload", response_model=UploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    username: str = Depends(verify_token)
):
    """
    Upload a PDF: validate → extract → chunk → embed → store in Pinecone.
    The local PDF file is deleted immediately after successful indexing —
    vectors live in Pinecone and persist across server restarts.
    """
    settings = get_settings()

    # Pre-write validation (extension, MIME, magic bytes, size, encryption, pages, text)
    validate_pdf_upload(file, settings)

    document_id = str(uuid.uuid4())
    storage_filename = f"{document_id}.pdf"
    file_path = (UPLOAD_DIR / storage_filename).resolve()

    # Path traversal guard
    if not file_path.is_relative_to(RESOLVED_UPLOAD_DIR):
        raise HTTPException(
            status_code=400,
            detail="Invalid filename or path traversal attempt detected."
        )

    try:
        # Write PDF to disk temporarily for text extraction
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        file_size = file_path.stat().st_size

        # Process in threadpool — text extraction + Gemini embedding calls are blocking
        result = await asyncio.to_thread(
            process_document,
            str(file_path),
            file.filename,
            document_id=document_id,
            storage_filename=storage_filename,
            size_bytes=file_size,
        )

        return UploadResponse(
            filename=file.filename,
            message="File indexed into Pinecone — embeddings are permanently stored.",
            size_bytes=file_size,
            chunk_count=result.chunk_count,
            embedding_count=result.embedding_count,
            embedding_dimensions=result.embedding_dimensions,
            collection_name=result.collection_name,
        )

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process file: {str(e)}"
        )
    finally:
        # Always delete the local file — vectors are in Pinecone (persistent)
        # PDF is not needed for querying
        if file_path.exists():
            file_path.unlink()


@router.delete("/{document_id}")
async def delete_uploaded_document(
    document_id: str,
    username: str = Depends(verify_token)
):
    """
    Delete a document from Pinecone by document_id.
    Local file is already deleted after indexing, so only Pinecone cleanup is needed.
    """
    try:
        storage_filename = delete_document(document_id)

        if not storage_filename:
            raise HTTPException(
                status_code=404,
                detail="Document not found."
            )

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