import asyncio
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.vector_store import semantic_search

router = APIRouter(
    prefix="/search",
    tags=["Search"],
)


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Natural language question or search phrase")
    top_k: int = Field(default=4, ge=1, le=20, description="Number of similar chunks to return")


class SearchResultItem(BaseModel):
    content: str
    source_file: str | None
    page: int | None
    score: float


class SearchResponse(BaseModel):
    query: str
    result_count: int
    results: list[SearchResultItem]


@router.post("", response_model=SearchResponse)
async def search_documents(request: SearchRequest):
    """
    Semantic search over ingested document chunks.
    Returns the most relevant text passages ranked by similarity.
    """
    try:
        results = await asyncio.to_thread(semantic_search, request.query, top_k=request.top_k)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")

    return SearchResponse(
        query=request.query,
        result_count=len(results),
        results=[
            SearchResultItem(
                content=result.content,
                source_file=result.source_file,
                page=result.page,
                score=result.score,
            )
            for result in results
        ],
    )
