import logging
import uuid
from dataclasses import dataclass
from functools import lru_cache

import google.generativeai as genai
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_pinecone import PineconeVectorStore
from pinecone import Pinecone, ServerlessSpec

from core.config import get_settings

logger = logging.getLogger(__name__)

# Gemini embedding-001 outputs 768-dimensional vectors
EMBEDDING_DIMENSION = 768

# Module-level flag — index only needs to be confirmed once per server lifetime
_index_ready: bool = False


# ==============================================================
# Embeddings
# ==============================================================

class GeminiEmbeddings(Embeddings):
    """Gemini REST embed API — used for both indexing and querying."""

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


# ==============================================================
# Data classes
# ==============================================================

@dataclass
class SearchResult:
    content: str
    source_file: str | None
    page: int | None
    score: float  # cosine similarity: 0.0–1.0, higher = more relevant


@dataclass
class IndexedDocument:
    document_id: str
    source_file: str
    storage_filename: str
    chunk_count: int
    pages: list[int]
    size_bytes: int | None


# ==============================================================
# Singletons
# ==============================================================

@lru_cache
def get_embeddings() -> GeminiEmbeddings:
    settings = get_settings()
    return GeminiEmbeddings(
        model=settings.embedding_model,
        api_key=settings.gemini_api_key,
    )


@lru_cache
def get_pinecone_client() -> Pinecone:
    settings = get_settings()
    return Pinecone(api_key=settings.pinecone_api_key)


def _ensure_index_exists() -> None:
    """
    Create the Pinecone serverless index if it does not exist.
    Uses a module-level flag so the check only runs once per server lifetime.
    """
    global _index_ready
    if _index_ready:
        return

    settings = get_settings()
    pc = get_pinecone_client()
    existing_names = [idx.name for idx in pc.list_indexes()]

    if settings.pinecone_index_name not in existing_names:
        logger.info("Pinecone index '%s' not found — creating.", settings.pinecone_index_name)
        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=EMBEDDING_DIMENSION,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        logger.info("Pinecone index '%s' created successfully.", settings.pinecone_index_name)
    else:
        logger.info("Pinecone index '%s' is ready.", settings.pinecone_index_name)

    _index_ready = True


@lru_cache
def get_vector_store() -> PineconeVectorStore:
    _ensure_index_exists()
    settings = get_settings()
    pc = get_pinecone_client()
    return PineconeVectorStore(
        index=pc.Index(settings.pinecone_index_name),
        embedding=get_embeddings(),
        text_key="text",
    )


def _get_raw_index():
    """Return the raw Pinecone Index object for direct metadata operations."""
    _ensure_index_exists()
    settings = get_settings()
    return get_pinecone_client().Index(settings.pinecone_index_name)


# ==============================================================
# Write operations
# ==============================================================

def store_documents(
    chunks: list[Document],
    filename: str,
    document_id: str,
    storage_filename: str,
    size_bytes: int = 0,
) -> int:
    """
    Embed and store document chunks in Pinecone.
    Uses the chunk_id from metadata as the Pinecone vector ID so we can
    delete by document_id prefix later.
    """
    for chunk in chunks:
        chunk.metadata["source_file"] = filename
        chunk.metadata["document_id"] = document_id
        chunk.metadata["storage_filename"] = storage_filename
        chunk.metadata["size_bytes"] = size_bytes

    # Use chunk_id as the actual Pinecone vector ID
    # Format: {document_id}_p{page}_c{idx}  — enables prefix-based deletion
    ids = [
        chunk.metadata.get("chunk_id") or str(uuid.uuid4())
        for chunk in chunks
    ]

    vectorstore = get_vector_store()
    result_ids = vectorstore.add_documents(chunks, ids=ids)
    return len(result_ids)


def delete_document(document_id: str) -> str | None:
    """
    Delete all Pinecone vectors belonging to document_id.
    Lists by ID prefix (document_id_p*) then deletes in batches.
    Returns storage_filename if found, None if document does not exist.
    """
    index = _get_raw_index()

    ids_to_delete: list[str] = []
    storage_filename: str | None = None

    # Chunk IDs are prefixed with document_id — e.g. "{uuid}_p1_c0"
    for id_batch in index.list(prefix=document_id):
        if not storage_filename and id_batch:
            # Fetch one vector to read the storage_filename from metadata
            fetch_result = index.fetch(ids=id_batch[:1])
            for _, vec_data in fetch_result.vectors.items():
                storage_filename = (vec_data.metadata or {}).get("storage_filename")
        ids_to_delete.extend(id_batch)

    if not ids_to_delete:
        return None

    # Delete in batches of 1000 (Pinecone per-request limit)
    for i in range(0, len(ids_to_delete), 1000):
        index.delete(ids=ids_to_delete[i : i + 1000])

    logger.info(
        "Deleted %d vectors for document_id=%s", len(ids_to_delete), document_id
    )
    return storage_filename or f"{document_id}.pdf"


# ==============================================================
# Read operations
# ==============================================================

def get_collection_stats() -> dict:
    index = _get_raw_index()
    stats = index.describe_index_stats()
    settings = get_settings()
    return {
        "collection_name": settings.pinecone_index_name,
        "chunk_count": stats.total_vector_count,
        "persist_directory": "pinecone-cloud",
    }


def list_indexed_documents() -> list[IndexedDocument]:
    """
    List all indexed documents by scanning Pinecone vector metadata.
    Fetches all vector IDs then reads metadata in batches of 100.
    """
    index = _get_raw_index()

    stats = index.describe_index_stats()
    if stats.total_vector_count == 0:
        return []

    # Collect all vector IDs
    all_ids: list[str] = []
    for id_batch in index.list():
        all_ids.extend(id_batch)

    if not all_ids:
        return []

    # Fetch metadata in batches (Pinecone fetch limit: 1000 per call)
    FETCH_BATCH_SIZE = 100
    document_map: dict[str, dict] = {}

    for i in range(0, len(all_ids), FETCH_BATCH_SIZE):
        batch = all_ids[i : i + FETCH_BATCH_SIZE]
        try:
            fetch_result = index.fetch(ids=batch)
        except Exception as e:
            logger.warning("Batch fetch error (skipping): %s", e)
            continue

        for _, vector_data in fetch_result.vectors.items():
            metadata = vector_data.metadata or {}
            doc_id = metadata.get("document_id")
            source_file = metadata.get("source_file")

            if not doc_id or not source_file:
                continue

            doc_id_str = str(doc_id)
            entry = document_map.setdefault(
                doc_id_str,
                {
                    "document_id": doc_id_str,
                    "source_file": str(source_file),
                    "storage_filename": str(
                        metadata.get("storage_filename", f"{doc_id_str}.pdf")
                    ),
                    "chunk_count": 0,
                    "pages": set(),
                    "size_bytes": metadata.get("size_bytes"),
                },
            )
            entry["chunk_count"] += 1

            page = metadata.get("page")
            if isinstance(page, int):
                entry["pages"].add(page)

    return [
        IndexedDocument(
            document_id=doc_id,
            source_file=str(d["source_file"]),
            storage_filename=str(d["storage_filename"]),
            chunk_count=int(d["chunk_count"]),
            pages=sorted(d["pages"]),
            size_bytes=d.get("size_bytes"),
        )
        for doc_id, d in sorted(
            document_map.items(), key=lambda x: str(x[1]["source_file"]).lower()
        )
    ]


def semantic_search(query: str, top_k: int | None = None) -> list[SearchResult]:
    """
    Semantic similarity search over all indexed document chunks.
    Returns cosine similarity scores (0.0–1.0; higher = more relevant).
    """
    settings = get_settings()
    k = top_k or settings.search_top_k

    index = _get_raw_index()
    stats = index.describe_index_stats()
    if stats.total_vector_count == 0:
        return []

    vectorstore = get_vector_store()
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
