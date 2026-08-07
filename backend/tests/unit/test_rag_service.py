from unittest.mock import MagicMock, patch

import pytest
from langchain_core.documents import Document

from services.rag_service import RAGService, process_document


# =====================================================
# chunk_documents()
# =====================================================

@patch("services.rag_service.get_settings")
def test_chunk_documents(mock_get_settings):
    settings = MagicMock()
    settings.chunk_size = 1000
    settings.chunk_overlap = 200

    mock_get_settings.return_value = settings

    service = RAGService()

    docs = [
        Document(
            page_content="This is a sample document.",
            metadata={
                "page": 1,
                "source_file": "policy.pdf",
            },
        )
    ]

    chunks = service.chunk_documents(docs, "policy.pdf")

    assert len(chunks) >= 1
    assert "chunk_id" in chunks[0].metadata
    assert "section_title" in chunks[0].metadata


# =====================================================
# process_document() Success
# =====================================================

@patch("services.rag_service.store_documents")
@patch.object(RAGService, "chunk_documents")
@patch.object(RAGService, "extract_text_from_pdf")
@patch("services.rag_service.get_settings")
def test_process_document_success(
    mock_get_settings,
    mock_extract,
    mock_chunk,
    mock_store,
):
    settings = MagicMock()
    settings.chunk_size = 1000
    settings.chunk_overlap = 200
    settings.chroma_collection_name = "enterprise_rag"

    mock_get_settings.return_value = settings

    documents = [
        Document(
            page_content="Page 1",
            metadata={},
        )
    ]

    chunks = [
        Document(
            page_content="Chunk 1",
            metadata={},
        )
    ]

    mock_extract.return_value = documents
    mock_chunk.return_value = chunks
    mock_store.return_value = 1

    result = process_document(
        "dummy.pdf",
        "policy.pdf",
    )

    assert result.chunk_count == 1
    assert result.embedding_count == 1
    assert result.embedding_dimensions == 768
    assert result.collection_name == "enterprise_rag"

    mock_extract.assert_called_once_with("dummy.pdf", "policy.pdf")
    mock_chunk.assert_called_once_with(documents, "policy.pdf")
    mock_store.assert_called_once_with(chunks, "policy.pdf")


# =====================================================
# process_document() Chroma Failure
# =====================================================

@patch("services.rag_service.store_documents")
@patch.object(RAGService, "chunk_documents")
@patch.object(RAGService, "extract_text_from_pdf")
@patch("services.rag_service.get_settings")
def test_process_document_store_failure(
    mock_get_settings,
    mock_extract,
    mock_chunk,
    mock_store,
):
    settings = MagicMock()
    settings.chunk_size = 1000
    settings.chunk_overlap = 200
    settings.chroma_collection_name = "enterprise_rag"

    mock_get_settings.return_value = settings

    documents = [
        Document(
            page_content="Page",
            metadata={},
        )
    ]

    chunks = [
        Document(
            page_content="Chunk",
            metadata={},
        )
    ]

    mock_extract.return_value = documents
    mock_chunk.return_value = chunks
    mock_store.side_effect = Exception("ChromaDB unavailable")

    with pytest.raises(RuntimeError, match="ChromaDB write failure"):
        process_document(
            "dummy.pdf",
            "policy.pdf",
        )

    mock_extract.assert_called_once_with("dummy.pdf", "policy.pdf")
    mock_chunk.assert_called_once_with(documents, "policy.pdf")
    mock_store.assert_called_once_with(chunks, "policy.pdf")