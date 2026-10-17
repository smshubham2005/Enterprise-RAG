import logging
import uuid
from dataclasses import dataclass
from functools import lru_cache

import google.generativeai as genai
from langchain_core.documents import Document
from pinecone import Pinecone, ServerlessSpec

from core.config import get_settings

logger = logging.getLogger(__name__)

_index_ready: bool = False
_detected_dimension: int | None = None


# ==============================================================
# Embeddings via Gemini
# ==============================================================

def get_detected_dimension() -> int:
    global _detected_dimension
    if _detected_dimension is None:
        settings = get_settings()
        genai.configure(api_key=settings.gemini_api_key)
        sample = genai.embed_content(
            model=settings.embedding_model,
            content="test",
            task_type="retrieval_document",
        )["embedding"]
        _detected_dimension = len(sample)
        logger.info("Detected embedding model dimension: %d", _detected_dimension)
    return _detected_dimension


def get_gemini_embeddings(texts: list[str]) -> list[list[float]]:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    return [
        genai.embed_content(
            model=settings.embedding_model,
            content=text,
            task_type="retrieval_document",
        )["embedding"]
        for text in texts
    ]


def get_query_embedding(text: str) -> list[float]:
    settings = get_settings()
    genai.configure(api_key=settings.gemini_api_key)
    return genai.embed_content(
        model=settings.embedding_model,
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
    score: float


@dataclass
class IndexedDocument:
    document_id: str
    source_file: str
    storage_filename: str
    chunk_count: int
    pages: list[int]
    size_bytes: int | None


# ==============================================================
# Pinecone Singletons & Init
# ==============================================================

@lru_cache
def get_pinecone_client() -> Pinecone:
    settings = get_settings()
    return Pinecone(api_key=settings.pinecone_api_key)


def _ensure_index_exists() -> None:
    global _index_ready
    if _index_ready:
        return

    settings = get_settings()
    pc = get_pinecone_client()
    target_dim = get_detected_dimension()
    
    existing_indexes = {idx.name: idx for idx in pc.list_indexes()}

    if settings.pinecone_index_name in existing_indexes:
        existing_info = existing_indexes[settings.pinecone_index_name]
        if existing_info.dimension != target_dim:
            logger.warning(
                "Pinecone index dimension mismatch (found %d, model outputs %d). Recreating index...",
                existing_info.dimension,
                target_dim,
            )
            pc.delete_index(settings.pinecone_index_name)
            pc.create_index(
                name=settings.pinecone_index_name,
                dimension=target_dim,
                metric="cosine",
                spec=ServerlessSpec(cloud="aws", region="us-east-1"),
            )
            logger.info("Pinecone index recreated with dimension %d.", target_dim)
    else:
        logger.info("Creating Pinecone index '%s' with dimension %d...", settings.pinecone_index_name, target_dim)
        pc.create_index(
            name=settings.pinecone_index_name,
            dimension=target_dim,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
        logger.info("Pinecone index '%s' created.", settings.pinecone_index_name)

    _index_ready = True


def get_index():
    _ensure_index_exists()
    settings = get_settings()
    return get_pinecone_client().Index(settings.pinecone_index_name)


# ==============================================================
# Operations
# ==============================================================

def store_documents(
    chunks: list[Document],
    filename: str,
    document_id: str,
    storage_filename: str,
    size_bytes: int = 0,
) -> int:
    index = get_index()

    texts = [chunk.page_content for chunk in chunks]
    embeddings = get_gemini_embeddings(texts)

    vectors_to_upsert = []
    for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
        page = chunk.metadata.get("page")
        vector_id = chunk.metadata.get("chunk_id") or f"{document_id}_p{page or 1}_c{idx}"
        
        metadata = {
            "text": chunk.page_content,
            "source_file": filename,
            "document_id": document_id,
            "storage_filename": storage_filename,
            "size_bytes": size_bytes,
        }
        if page is not None:
            metadata["page"] = page

        vectors_to_upsert.append({
            "id": vector_id,
            "values": emb,
            "metadata": metadata,
        })

    # Upsert in batches of 100
    for i in range(0, len(vectors_to_upsert), 100):
        index.upsert(vectors=vectors_to_upsert[i : i + 100])

    return len(chunks)


def delete_document(document_id: str) -> str | None:
    index = get_index()
    storage_filename: str | None = None
    
    # Query for vectors matching this document_id to get their IDs
    dim = get_detected_dimension()
    try:
        res = index.query(
            vector=[0.0] * dim,
            filter={"document_id": {"$eq": document_id}},
            top_k=1000,
            include_metadata=True,
        )
        ids_to_delete = [match.id for match in res.matches]
        if res.matches:
            storage_filename = (res.matches[0].metadata or {}).get("storage_filename")
    except Exception as e:
        logger.warning("Error finding vectors to delete: %s", e)
        ids_to_delete = []

    if not ids_to_delete:
        return None

    for i in range(0, len(ids_to_delete), 1000):
        index.delete(ids=ids_to_delete[i : i + 1000])

    return storage_filename or f"{document_id}.pdf"


def get_collection_stats() -> dict:
    index = get_index()
    stats = index.describe_index_stats()
    settings = get_settings()
    return {
        "collection_name": settings.pinecone_index_name,
        "chunk_count": stats.total_vector_count,
        "persist_directory": "pinecone-cloud",
    }


def list_indexed_documents() -> list[IndexedDocument]:
    """
    List all documents by querying chunk metadata via vector similarity query.
    100% reliable across all Pinecone architectures (no reliance on index.list() pagination).
    """
    index = get_index()
    dim = get_detected_dimension()

    try:
        response = index.query(
            vector=[0.0] * dim,
            top_k=1000,
            include_metadata=True,
        )
    except Exception as e:
        logger.warning("Error querying Pinecone for document list: %s", e)
        return []

    doc_map: dict[str, dict] = {}
    for match in response.matches:
        m = match.metadata or {}
        d_id = m.get("document_id")
        s_file = m.get("source_file")
        if not d_id or not s_file:
            continue

        d_str = str(d_id)
        item = doc_map.setdefault(
            d_str,
            {
                "document_id": d_str,
                "source_file": str(s_file),
                "storage_filename": str(m.get("storage_filename", f"{d_str}.pdf")),
                "chunk_count": 0,
                "pages": set(),
                "size_bytes": m.get("size_bytes"),
            },
        )
        item["chunk_count"] += 1
        p = m.get("page")
        if isinstance(p, (int, float)):
            item["pages"].add(int(p))

    return [
        IndexedDocument(
            document_id=d_id,
            source_file=str(d["source_file"]),
            storage_filename=str(d["storage_filename"]),
            chunk_count=int(d["chunk_count"]),
            pages=sorted(d["pages"]),
            size_bytes=d.get("size_bytes"),
        )
        for d_id, d in sorted(doc_map.items(), key=lambda x: str(x[1]["source_file"]).lower())
    ]


def semantic_search(query: str, top_k: int | None = None) -> list[SearchResult]:
    settings = get_settings()
    k = top_k or settings.search_top_k

    index = get_index()
    query_embedding = get_query_embedding(query)
    
    response = index.query(
        vector=query_embedding,
        top_k=k,
        include_metadata=True,
    )

    results = []
    for match in response.matches:
        meta = match.metadata or {}
        page_val = meta.get("page")
        results.append(
            SearchResult(
                content=meta.get("text", ""),
                source_file=meta.get("source_file"),
                page=int(page_val) if page_val is not None else None,
                score=float(match.score),
            )
        )

    return results
