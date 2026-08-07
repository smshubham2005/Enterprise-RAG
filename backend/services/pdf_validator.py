import io
import os
from fastapi import UploadFile, HTTPException
from pypdf import PdfReader
from core.config import Settings

def validate_pdf_upload(file: UploadFile, settings: Settings) -> None:
    """
    Validate an uploaded PDF file stream BEFORE saving to disk.
    
    Validates:
    1. File extension (.pdf)
    2. MIME type (application/pdf)
    3. Non-empty file size
    4. Maximum file size (MAX_UPLOAD_SIZE_MB)
    5. PDF header magic bytes (%PDF-)
    6. PDF encryption status
    7. PDF page count (MAX_PDF_PAGES)
    8. PDF text readability & maximum character count (MAX_EXTRACTED_TEXT_CHARS)
    """
    filename = file.filename or ""
    
    # 1. Extension Check
    if not filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are supported."
        )

    # 2. MIME Type Check (if provided by client)
    if file.content_type and file.content_type.lower() not in ["application/pdf", "application/x-pdf"]:
        raise HTTPException(
            status_code=400,
            detail="Invalid content type. Uploaded file must be application/pdf."
        )

    # 3. Size Check
    file.file.seek(0, os.SEEK_END)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size == 0:
        raise HTTPException(
            status_code=400,
            detail="Uploaded file is empty."
        )

    max_size_bytes = settings.max_upload_size_mb * 1024 * 1024
    if file_size > max_size_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File size exceeds maximum allowed limit of {settings.max_upload_size_mb}MB."
        )

    # 4. Magic Bytes Check (%PDF-)
    header = file.file.read(5)
    file.file.seek(0)
    
    if not header.startswith(b"%PDF-"):
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file header magic bytes."
        )

    # 5. PDF Structure & Readability Validation using pypdf
    try:
        reader = PdfReader(file.file)
        
        if reader.is_encrypted:
            raise HTTPException(
                status_code=400,
                detail="Uploaded PDF is encrypted or password-protected. Please upload an unencrypted file."
            )

        total_pages = len(reader.pages)
        if total_pages == 0:
            raise HTTPException(
                status_code=400,
                detail="Uploaded PDF file contains no pages."
            )

        if total_pages > settings.max_pdf_pages:
            raise HTTPException(
                status_code=400,
                detail=f"PDF exceeds maximum allowed limit of {settings.max_pdf_pages} pages (found {total_pages} pages)."
            )

        # Validate text extraction & total text length bounds
        total_text_length = 0
        for page in reader.pages:
            try:
                text = page.extract_text() or ""
                total_text_length += len(text)
                if total_text_length > settings.max_extracted_text_chars:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Extracted text exceeds maximum limit of {settings.max_extracted_text_chars} characters."
                    )
            except Exception as page_err:
                continue

    except HTTPException:
        raise
    except Exception as err:
        raise HTTPException(
            status_code=400,
            detail="PDF file is corrupted or unreadable."
        )
    finally:
        # Reset stream position for downstream file operations
        file.file.seek(0)
