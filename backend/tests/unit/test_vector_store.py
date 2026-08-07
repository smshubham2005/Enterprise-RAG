from unittest.mock import MagicMock, patch

from langchain_core.documents import Document

from services.vector_store import (
    get_embeddings,
    get_vector_store,
    store_documents,
    get_collection_stats,
    list_indexed_documents,
    semantic_search,
)


# =====================================================
# get_embeddings()
# =====================================================

@patch("services.vector_store.get_settings")
@patch("services.vector_store.GeminiEmbeddings")
def test_get_embeddings(mock_embeddings, mock_settings):

    settings = MagicMock()
    settings.embedding_model = "embedding-model"
    settings.gemini_api_key = "fake-key"

    mock_settings.return_value = settings

    get_embeddings.cache_clear()

    get_embeddings()

    mock_embeddings.assert_called_once_with(
        model="embedding-model",
        api_key="fake-key",
    )


# =====================================================
# get_vector_store()
# =====================================================

@patch("services.vector_store.get_embeddings")
@patch("services.vector_store.get_settings")
@patch("services.vector_store.Chroma")
def test_get_vector_store(
    mock_chroma,
    mock_settings,
    mock_embeddings,
):

    settings = MagicMock()
    settings.chroma_collection_name = "test_collection"
    settings.chroma_persist_dir = MagicMock()

    mock_settings.return_value = settings

    get_vector_store()

    settings.chroma_persist_dir.mkdir.assert_called_once_with(
        parents=True,
        exist_ok=True,
    )

    mock_chroma.assert_called_once()


# =====================================================
# store_documents()
# =====================================================

@patch("services.vector_store.get_vector_store")
def test_store_documents(mock_get_vector_store):

    vector_store = MagicMock()

    vector_store.add_documents.return_value = [
        "1",
        "2",
    ]

    mock_get_vector_store.return_value = vector_store

    docs = [
        Document(
            page_content="Chunk 1",
            metadata={},
        ),
        Document(
            page_content="Chunk 2",
            metadata={},
        ),
    ]

    count = store_documents(
        docs,
        "policy.pdf",
    )

    assert count == 2

    vector_store.add_documents.assert_called_once()

    for doc in docs:
        assert doc.metadata["source_file"] == "policy.pdf"


# =====================================================
# store_documents() Empty List
# =====================================================

@patch("services.vector_store.get_vector_store")
def test_store_documents_empty(mock_get_vector_store):

    vector_store = MagicMock()

    vector_store.add_documents.return_value = []

    mock_get_vector_store.return_value = vector_store

    result = store_documents(
        [],
        "empty.pdf",
    )

    assert result == 0

    vector_store.add_documents.assert_called_once_with([])


# =====================================================
# get_collection_stats()
# =====================================================

@patch("services.vector_store.get_vector_store")
@patch("services.vector_store.get_settings")
def test_get_collection_stats(
    mock_settings,
    mock_get_vector_store,
):

    settings = MagicMock()
    settings.chroma_collection_name = "enterprise_rag"
    settings.chroma_persist_dir = "backend/chroma_db"

    mock_settings.return_value = settings

    vector_store = MagicMock()
    vector_store._collection.count.return_value = 15

    mock_get_vector_store.return_value = vector_store

    stats = get_collection_stats()

    assert stats["collection_name"] == "enterprise_rag"
    assert stats["chunk_count"] == 15
    assert stats["persist_directory"] == "backend/chroma_db"


# =====================================================
# list_indexed_documents()
# =====================================================

@patch("services.vector_store.get_vector_store")
def test_list_indexed_documents(mock_get_vector_store):

    vector_store = MagicMock()

    vector_store._collection.count.return_value = 3

    vector_store._collection.get.return_value = {
        "metadatas": [
            {
                "source_file": "policy.pdf",
                "page": 1,
            },
            {
                "source_file": "policy.pdf",
                "page": 2,
            },
            {
                "source_file": "guide.pdf",
                "page": 1,
            },
        ]
    }

    mock_get_vector_store.return_value = vector_store

    documents = list_indexed_documents()

    assert len(documents) == 2

    policy = next(
        doc
        for doc in documents
        if doc.source_file == "policy.pdf"
    )

    assert policy.chunk_count == 2
    assert policy.pages == [1, 2]

    guide = next(
        doc
        for doc in documents
        if doc.source_file == "guide.pdf"
    )

    assert guide.chunk_count == 1
    assert guide.pages == [1]


# =====================================================
# list_indexed_documents() Empty Collection
# =====================================================

@patch("services.vector_store.get_vector_store")
def test_list_indexed_documents_empty(
    mock_get_vector_store,
):

    vector_store = MagicMock()

    vector_store._collection.count.return_value = 0

    mock_get_vector_store.return_value = vector_store

    documents = list_indexed_documents()

    assert documents == []

# =====================================================
# semantic_search()
# =====================================================

@patch("services.vector_store.get_vector_store")
@patch("services.vector_store.get_settings")
def test_semantic_search(
    mock_settings,
    mock_get_vector_store,
):

    settings = MagicMock()
    settings.search_top_k = 4

    mock_settings.return_value = settings

    vector_store = MagicMock()

    vector_store._collection.count.return_value = 2

    vector_store.similarity_search_with_score.return_value = [
        (
            Document(
                page_content="Returns are accepted within 30 days.",
                metadata={
                    "source_file": "policy.pdf",
                    "page": 1,
                },
            ),
            0.08,
        ),
        (
            Document(
                page_content="Refund processing takes 5-7 business days.",
                metadata={
                    "source_file": "policy.pdf",
                    "page": 2,
                },
            ),
            0.15,
        ),
    ]

    mock_get_vector_store.return_value = vector_store

    results = semantic_search("refund")

    assert len(results) == 2

    assert results[0].content == "Returns are accepted within 30 days."
    assert results[0].source_file == "policy.pdf"
    assert results[0].page == 1
    assert results[0].score == 0.08

    vector_store.similarity_search_with_score.assert_called_once_with(
        "refund",
        k=4,
    )


# =====================================================
# semantic_search() Empty Collection
# =====================================================

@patch("services.vector_store.get_vector_store")
@patch("services.vector_store.get_settings")
def test_semantic_search_empty(
    mock_settings,
    mock_get_vector_store,
):

    settings = MagicMock()
    settings.search_top_k = 4

    mock_settings.return_value = settings

    vector_store = MagicMock()

    vector_store._collection.count.return_value = 0

    mock_get_vector_store.return_value = vector_store

    results = semantic_search("refund")

    assert results == []


# =====================================================
# semantic_search() Custom top_k
# =====================================================

@patch("services.vector_store.get_vector_store")
@patch("services.vector_store.get_settings")
def test_semantic_search_custom_top_k(
    mock_settings,
    mock_get_vector_store,
):

    settings = MagicMock()
    settings.search_top_k = 4

    mock_settings.return_value = settings

    vector_store = MagicMock()

    vector_store._collection.count.return_value = 1

    vector_store.similarity_search_with_score.return_value = []

    mock_get_vector_store.return_value = vector_store

    semantic_search(
        "refund",
        top_k=2,
    )

    vector_store.similarity_search_with_score.assert_called_once_with(
        "refund",
        k=2,
    )