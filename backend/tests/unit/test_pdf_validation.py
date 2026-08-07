import io
from unittest.mock import MagicMock, patch
import pytest
from fastapi import HTTPException, UploadFile

from core.config import Settings
from services.pdf_validator import validate_pdf_upload

@pytest.fixture
def mock_settings():
    return Settings(
        gemini_api_key="test-key",
        jwt_secret_key="secret",
        admin_password_hash="hash",
        max_upload_size_mb=2,
        max_pdf_pages=5,
        max_extracted_text_chars=100
    )

def create_mock_upload_file(filename: str, content: bytes, content_type: str = "application/pdf") -> UploadFile:
    spool = io.BytesIO(content)
    upload_file = UploadFile(filename=filename, file=spool, headers={"content-type": content_type})
    upload_file.content_type = content_type
    return upload_file

def test_validate_non_pdf_extension(mock_settings):
    file = create_mock_upload_file("script.py", b"%PDF-1.4 test")
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_upload(file, mock_settings)
    assert exc_info.value.status_code == 400
    assert "Only PDF files are supported" in exc_info.value.detail

def test_validate_invalid_mime_type(mock_settings):
    file = create_mock_upload_file("document.pdf", b"%PDF-1.4 test", content_type="text/plain")
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_upload(file, mock_settings)
    assert exc_info.value.status_code == 400
    assert "Invalid content type" in exc_info.value.detail

def test_validate_empty_file(mock_settings):
    file = create_mock_upload_file("empty.pdf", b"")
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_upload(file, mock_settings)
    assert exc_info.value.status_code == 400
    assert "empty" in exc_info.value.detail

def test_validate_oversized_file(mock_settings):
    # Create 3MB content for 2MB limit
    content = b"%PDF-1.4 " + (b"A" * (3 * 1024 * 1024))
    file = create_mock_upload_file("large.pdf", content)
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_upload(file, mock_settings)
    assert exc_info.value.status_code == 400
    assert "exceeds maximum allowed limit" in exc_info.value.detail

def test_validate_invalid_magic_bytes(mock_settings):
    file = create_mock_upload_file("fake.pdf", b"NOT_A_PDF_HEADER_DATA")
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_upload(file, mock_settings)
    assert exc_info.value.status_code == 400
    assert "Invalid PDF file header magic bytes" in exc_info.value.detail

@patch("services.pdf_validator.PdfReader")
def test_validate_encrypted_pdf(mock_reader_cls, mock_settings):
    mock_reader = MagicMock()
    mock_reader.is_encrypted = True
    mock_reader_cls.return_value = mock_reader
    
    file = create_mock_upload_file("encrypted.pdf", b"%PDF-1.4 encrypted data")
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_upload(file, mock_settings)
    assert exc_info.value.status_code == 400
    assert "encrypted" in exc_info.value.detail

@patch("services.pdf_validator.PdfReader")
def test_validate_page_count_exceeded(mock_reader_cls, mock_settings):
    mock_reader = MagicMock()
    mock_reader.is_encrypted = False
    mock_reader.pages = [MagicMock()] * 10 # Limit is 5
    mock_reader_cls.return_value = mock_reader
    
    file = create_mock_upload_file("many_pages.pdf", b"%PDF-1.4 data")
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_upload(file, mock_settings)
    assert exc_info.value.status_code == 400
    assert "exceeds maximum allowed limit of 5 pages" in exc_info.value.detail

@patch("services.pdf_validator.PdfReader")
def test_validate_text_length_exceeded(mock_reader_cls, mock_settings):
    mock_reader = MagicMock()
    mock_reader.is_encrypted = False
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "X" * 200 # Limit is 100
    mock_reader.pages = [mock_page]
    mock_reader_cls.return_value = mock_reader
    
    file = create_mock_upload_file("huge_text.pdf", b"%PDF-1.4 data")
    with pytest.raises(HTTPException) as exc_info:
        validate_pdf_upload(file, mock_settings)
    assert exc_info.value.status_code == 400
    assert "Extracted text exceeds maximum limit" in exc_info.value.detail

@patch("services.pdf_validator.PdfReader")
def test_validate_valid_pdf_success(mock_reader_cls, mock_settings):
    mock_reader = MagicMock()
    mock_reader.is_encrypted = False
    mock_page = MagicMock()
    mock_page.extract_text.return_value = "Valid page content"
    mock_reader.pages = [mock_page]
    mock_reader_cls.return_value = mock_reader
    
    file = create_mock_upload_file("valid.pdf", b"%PDF-1.4 valid pdf content")
    # Should complete without throwing any exception
    validate_pdf_upload(file, mock_settings)
    assert file.file.tell() == 0 # Stream position reset
