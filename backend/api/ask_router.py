import asyncio
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field

from services.qa_service import answer_question
from api.auth_router import verify_token

router = APIRouter(
    prefix="/ask",
    tags=["RAG"],
)


class ChatMessage(BaseModel):
    role: str = Field(..., description="Role of the sender, either 'user' or 'assistant'")
    content: str = Field(..., description="Message content")


class AskRequest(BaseModel):
    query: str = Field(..., min_length=1, description="Question to answer from uploaded documents")
    top_k: int = Field(default=4, ge=1, le=20, description="Number of chunks to use as context")
    history: list[ChatMessage] = Field(default_factory=list, description="Previous chat message history")


class SourceSnippetResponse(BaseModel):
    content: str
    source_file: str | None
    page: int | None
    score: float


class AskResponse(BaseModel):
    query: str
    answer: str
    source_count: int
    sources: list[SourceSnippetResponse]


@router.post("", response_model=AskResponse)
async def ask_documents(request: AskRequest, username: str = Depends(verify_token)):
    """
    Answer a question using chat history, retrieved document context, and Gemini generation.
    """
    try:
        # Convert Pydantic ChatMessage history list to list of dicts for qa_service
        history_dicts = [{"role": msg.role, "content": msg.content} for msg in request.history]
        result = await asyncio.to_thread(answer_question, request.query, history=history_dicts, top_k=request.top_k)
    except Exception as error:
        raise HTTPException(status_code=500, detail=f"Answer generation failed: {str(error)}")

    return AskResponse(
        query=result.query,
        answer=result.answer,
        source_count=result.source_count,
        sources=[
            SourceSnippetResponse(
                content=source.content,
                source_file=source.source_file,
                page=source.page,
                score=source.score,
            )
            for source in result.sources
        ],
    )
