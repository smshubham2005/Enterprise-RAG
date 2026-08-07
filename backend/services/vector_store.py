from dataclasses import dataclass

from functools import lru_cache

import google.generativeai as genai
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from core.config import get_settings


class GeminiEmbeddings(Embeddings):
    """Use the Gemini REST embed API directly; LangChain's gRPC client times out locally."""

    def __init__(self, model: str, api_key: str) -> None:
        genai.configure(api_key=api_key)
        self.model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [
            genai.embed_content(
                model=self.model,
                content=text,
                task_type="retrieval_document",
            )["embedding"]
            for text in texts
        ]

    def embed_query(self, text: str) -> list[float]:
        return genai.embed_content(
            model=self.model,
            content=text,
            task_type="retrieval_query",
        )["embedding"]


@dataclass
class SearchResult:
    content: str
    source_file: str | None
    page: int | None
    score: float


@dataclass
class IndexedDocument:
    document_id: str
    source_file: str
    storage_filename: str
    chunk_count: int
    pages: list[int]


@lru_cache
def get_embeddings() -> GeminiEmbeddings:
    settings = get_settings()
    return GeminiEmbeddings(
        model=settings.embedding_model,
        api_key=settings.gemini_api_key,
    )


@lru_cache
def get_vector_store() -> Chroma:
    settings = get_settings()
    settings.chroma_persist_dir.mkdir(parents=True, exist_ok=True)

    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(settings.chroma_persist_dir),
    )


def store_documents(chunks: list[Document], filename: str, document_id: str, storage_filename: str) -> int:
    for chunk in chunks:
        chunk.metadata["source_file"] = filename
        chunk.metadata["document_id"] = document_id
        chunk.metadata["storage_filename"] = storage_filename

    vectorstore = get_vector_store()
    ids = vectorstore.add_documents(chunks)
    return len(ids)


def get_collection_stats() -> dict:
    settings = get_settings()
    vectorstore = get_vector_store()

    return {
        "collection_name": settings.chroma_collection_name,
        "chunk_count": vectorstore._collection.count(),
        "persist_directory": str(settings.chroma_persist_dir),
    }


def list_indexed_documents() -> list[IndexedDocument]:
    vectorstore = get_vector_store()

    if vectorstore._collection.count() == 0:
        return []

    collection_data = vectorstore._collection.get(include=["metadatas"])
    document_map: dict[str, dict[str, object]] = {}

    for metadata in collection_data.get("metadatas") or []:
        if not metadata:
            continue

        doc_id = metadata.get("document_id")
        source_file = metadata.get("source_file")
        storage_filename = metadata.get("storage_filename")

        if not doc_id or not source_file:
            continue

        doc_id_str = str(doc_id)
        document = document_map.setdefault(
            doc_id_str,
            {
                "document_id": doc_id_str,
                "source_file": str(source_file),
                "storage_filename": str(storage_filename or f"{doc_id_str}.pdf"),
                "chunk_count": 0,
                "pages": set(),
            },
        )
        document["chunk_count"] = int(document["chunk_count"]) + 1

        page = metadata.get("page")
        if isinstance(page, int):
            document["pages"].add(page)

    return [
        IndexedDocument(
            document_id=doc_id,
            source_file=str(doc_data["source_file"]),
            storage_filename=str(doc_data["storage_filename"]),
            chunk_count=int(doc_data["chunk_count"]),
            pages=sorted(doc_data["pages"]),
        )
        for doc_id, doc_data in sorted(document_map.items(), key=lambda x: str(x[1]["source_file"]).lower())
    ]


def semantic_search(query: str, top_k: int | None = None) -> list[SearchResult]:
    """
    Find the most semantically similar chunks to the user's query.
    Lower scores indicate closer matches (Chroma L2 distance).
    """
    settings = get_settings()
    k = top_k or settings.search_top_k
    vectorstore = get_vector_store()

    if vectorstore._collection.count() == 0:
        return []

    results = vectorstore.similarity_search_with_score(query, k=k)

    return [
        SearchResult(
            content=doc.page_content,
            source_file=doc.metadata.get("source_file"),
            page=doc.metadata.get("page"),
            score=float(score),
        )
        for doc, score in results
    ]

# ==========================================================
# DELETE DOCUMENT FROM CHROMADB
# ==========================================================

def delete_document(document_id: str) -> str | None:
    """
    Delete all vector embeddings belonging to a document_id.

    Returns:
        storage_filename if found and deleted, None otherwise.
    """

    vectorstore = get_vector_store()

    collection = vectorstore._collection

    # Find all chunks belonging to this document_id
    result = collection.get(
        where={"document_id": document_id},
        include=["metadatas"]
    )

    ids = result.get("ids", [])

    if not ids:
        return None

    metadatas = result.get("metadatas") or []
    storage_filename = None
    if metadatas and metadatas[0]:
        storage_filename = metadatas[0].get("storage_filename")

    collection.delete(ids=ids)

    return storage_filename or f"{document_id}.pdf"

