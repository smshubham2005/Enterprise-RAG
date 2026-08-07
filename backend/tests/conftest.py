"""
Shared pytest fixtures and mocks for all tests.

This module provides:
- Mocked Gemini API clients (embedding and generation)
- Test data (sample PDFs, mock responses)
- Environment configuration for testing
"""

import os
import pytest
from unittest.mock import MagicMock, patch
from pathlib import Path
import tempfile
from langchain_core.documents import Document


# ==========================================
# Environment & Configuration
# ==========================================

@pytest.fixture(scope="session")
def test_env():
    """Set up test environment variables."""
    os.environ["GEMINI_API_KEY"] = "test-key-xyz123"
    yield
    # Cleanup is implicit (test env only)


@pytest.fixture
def test_temp_dir():
    """Create a temporary directory for test uploads."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# ==========================================
# Mocked Gemini API
# ==========================================

@pytest.fixture
def mock_gemini_embeddings():
    """Mock GoogleGenerativeAI embedding function.
    
    Returns realistic 768-dimensional embedding vectors.
    """
    def embed_content(model, content, task_type):
        # Return a consistent 768-dim vector based on content hash
        # This ensures reproducible tests while simulating real embeddings
        hash_val = hash(content) % 100
        base_vector = [0.1 + (hash_val % 10) * 0.01] * 768
        return {"embedding": base_vector}
    
    return embed_content


@pytest.fixture
def mock_gemini_generation():
    """Mock GoogleGenerativeAI generation function.
    
    Returns realistic LLM-like responses without actual API calls.
    """
    def invoke_prompt(prompt):
        """Simulate Gemini generation based on prompt keywords."""
        response = MagicMock()
        
        # Simple heuristic-based responses for testing
        if "condense" in prompt.lower() or "standalone" in prompt.lower():
            response.content = "What is the main topic of this document?"
        elif "refund" in prompt.lower():
            response.content = "Returns are accepted within 30 days [Source 1]."
        elif "no readable text" in prompt.lower():
            response.content = "I could not find relevant information in the documents."
        else:
            response.content = "This is a test answer based on the provided context [Source 1]."
        
        return response
    
    return invoke_prompt


@pytest.fixture
def mock_chroma_collection():
    """Mock ChromaDB collection for testing.
    
    Provides in-memory simulation of ChromaDB without persistence.
    """
    class MockCollection:
        def __init__(self):
            self.documents = {}  # id -> document mapping
            self.metadata = {}   # id -> metadata mapping
        
        def add_documents(self, ids, documents, metadatas=None, embeddings=None):
            """Simulate adding documents to collection."""
            for doc_id, doc in zip(ids, documents):
                self.documents[doc_id] = doc
                self.metadata[doc_id] = metadatas.get(doc_id) if metadatas else {}
            return ids
        
        def query(self, query_embeddings, n_results=4):
            """Simulate similarity search."""
            # Return all stored documents up to n_results
            doc_ids = list(self.documents.keys())[:n_results]
            return {
                "ids": [doc_ids],
                "documents": [[self.documents[did] for did in doc_ids]],
                "metadatas": [[self.metadata[did] for did in doc_ids]],
                "distances": [[0.1 * i for i in range(len(doc_ids))]],
            }
        
        def count(self):
            """Return document count."""
            return len(self.documents)
        
        def get(self, include=None):
            """Return all documents with metadata."""
            return {
                "ids": list(self.documents.keys()),
                "documents": list(self.documents.values()),
                "metadatas": [self.metadata[did] for did in self.documents.keys()],
            }
    
    return MockCollection()


# ==========================================
# Test Data
# ==========================================

@pytest.fixture
def sample_documents():
    """Create sample LangChain Document objects for testing."""
    return [
        Document(
            page_content="Returns are accepted within 30 days of purchase. Customers must provide original receipt.",
            metadata={"source_file": "policy.pdf", "page": 1, "total_pages": 10}
        ),
        Document(
            page_content="Refund processing takes 5-7 business days. Expedited refunds available for premium members.",
            metadata={"source_file": "policy.pdf", "page": 2, "total_pages": 10}
        ),
        Document(
            page_content="Contact customer service at support@example.com for refund status inquiries.",
            metadata={"source_file": "policy.pdf", "page": 3, "total_pages": 10}
        ),
    ]


@pytest.fixture
def sample_chunks():
    """Create sample text chunks from RAG service."""
    return [
        Document(
            page_content="Returns are accepted within 30 days.",
            metadata={
                "source_file": "policy.pdf",
                "page": 1,
                "total_pages": 10,
                "chunk_id": "policy.pdf_p1_c0",
                "section_title": "Page 1 Section",
            }
        ),
        Document(
            page_content="Customers must provide original receipt.",
            metadata={
                "source_file": "policy.pdf",
                "page": 1,
                "total_pages": 10,
                "chunk_id": "policy.pdf_p1_c1",
                "section_title": "Page 1 Section",
            }
        ),
        Document(
            page_content="Refund processing takes 5-7 business days.",
            metadata={
                "source_file": "policy.pdf",
                "page": 2,
                "total_pages": 10,
                "chunk_id": "policy.pdf_p2_c0",
                "section_title": "Page 2 Section",
            }
        ),
    ]


@pytest.fixture
def chat_history():
    """Create sample chat history for multi-turn testing."""
    return [
        {"role": "user", "content": "What is your return policy?"},
        {"role": "assistant", "content": "Returns are accepted within 30 days."},
        {"role": "user", "content": "How long does refund take?"},
    ]


# ==========================================
# Patched Services
# ==========================================

@pytest.fixture
def patched_settings(monkeypatch, test_env):
    """Patch Settings to use test environment."""
    mock_settings = MagicMock()
    mock_settings.gemini_api_key = "test-key-xyz123"
    mock_settings.embedding_model = "models/embedding-001"
    mock_settings.generation_model = "gemini-1.5-flash"
    mock_settings.generation_temperature = 0.0
    mock_settings.chunk_size = 1000
    mock_settings.chunk_overlap = 200
    mock_settings.chroma_collection_name = "test_collection"
    mock_settings.search_top_k = 4
    
    monkeypatch.setattr("core.config.get_settings", lambda: mock_settings)
    return mock_settings


@pytest.fixture
def patched_embeddings(mock_gemini_embeddings):
    """Patch GeminiEmbeddings to use mock."""
    mock_instance = MagicMock()
    mock_instance.embed_documents = lambda texts: [
        mock_gemini_embeddings(
            model="models/embedding-001",
            content=text,
            task_type="retrieval_document"
        )["embedding"]
        for text in texts
    ]
    mock_instance.embed_query = lambda text: mock_gemini_embeddings(
        model="models/embedding-001",
        content=text,
        task_type="retrieval_query"
    )["embedding"]
    
    return mock_instance


@pytest.fixture
def patched_vector_store(mock_chroma_collection, patched_embeddings):
    """Patch Chroma to use mock collection."""
    mock_instance = MagicMock()
    mock_instance._collection = mock_chroma_collection
    mock_instance.add_documents = lambda docs: [f"doc_{i}" for i in range(len(docs))]
    mock_instance.similarity_search_with_score = lambda query, k=4: [
        (doc, 0.1 * i)
        for i, doc in enumerate([
            Document(
                page_content="Returns are accepted within 30 days.",
                metadata={"source_file": "policy.pdf", "page": 1}
            ),
            Document(
                page_content="Refund processing takes 5-7 business days.",
                metadata={"source_file": "policy.pdf", "page": 2}
            ),
        ][:k])
    ]
    
    return mock_instance


# ==========================================
# File Fixtures
# ==========================================

@pytest.fixture
def sample_pdf_path(test_temp_dir):
    """Create a path for a sample PDF (not actually created, just used for testing paths)."""
    # Note: For actual PDF testing, we'd need a real PDF file or mock PyPDFReader
    pdf_path = test_temp_dir / "sample.pdf"
    return pdf_path


# ==========================================
# Pytest Configuration
# ==========================================

def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "unit: mark test as a unit test (isolated, mocked dependencies)"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as an integration test (real services)"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow (use -m 'not slow' to skip)"
    )
