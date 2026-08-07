from dataclasses import dataclass
from functools import lru_cache

from langchain_google_genai import ChatGoogleGenerativeAI

from core.config import get_settings
from services.vector_store import SearchResult, semantic_search


@dataclass
class SourceSnippet:
    content: str
    source_file: str | None
    page: int |None
    score: float


@dataclass
class AnswerResult:
    query: str
    answer: str
    source_count: int
    sources: list[SourceSnippet]


@lru_cache
def get_chat_model() -> ChatGoogleGenerativeAI:
    settings = get_settings()
    return ChatGoogleGenerativeAI(
        model=settings.generation_model,
        google_api_key=settings.gemini_api_key,
        temperature=settings.generation_temperature,
    )


def answer_question(
    query: str,
    history: list[dict] | None = None,
    top_k: int | None = None,
) -> AnswerResult:
    """
    Generate a grounded answer from the most relevant document chunks.
    """

    history_list = history or []

    # Only condense follow-up questions when history exists AND condensation is required
    if history_list and _should_condense_query(query):
        search_query = _condense_query(query, history_list)
    else:
        search_query = query

    # Determine retrieval depth based on query type
    summary_keywords = [
        "summarize",
        "summary",
        "overview",
        "main points",
        "key points",
        "important points",
        "main topics",
    ]

    effective_top_k = top_k

    if effective_top_k is None:
        effective_top_k = (
            10
            if any(
                keyword in search_query.lower()
                for keyword in summary_keywords
            )
            else 4
        )

    search_results = semantic_search(
        search_query,
        top_k=effective_top_k,
    )

    sources = [
        SourceSnippet(
            content=result.content,
            source_file=result.source_file,
            page=result.page,
            score=result.score,
        )
        for result in search_results
    ]

    if not search_results:
        return AnswerResult(
            query=query,
            answer="I could not find any relevant document context to answer this question.",
            source_count=0,
            sources=[],
        )

    prompt = _build_grounded_prompt(
        query,
        search_results,
        history_list,
    )

    response = get_chat_model().invoke(prompt)

    answer = (
    response.content
    if isinstance(response.content, str)
    else str(response.content)
    ).strip()

    no_answer_phrases = [
    "do not contain enough information",
    "not enough information",
    "cannot answer",
    "can't answer",
    "unable to answer",
        ]

    if any(phrase in answer.lower() for phrase in no_answer_phrases):
        sources = []

    return AnswerResult(
    query=query,
    answer=answer,
    source_count=len(sources),
    sources=sources,
    )


REFERENTIAL_PATTERNS = {
    "it", "this", "that", "these", "those", "they", "them", "their",
    "its", "him", "her", "his", "hers", "he", "she",
    "more", "else", "above", "previous", "former", "latter", "again",
    "same", "other", "second", "third"
}


def _should_condense_query(query: str) -> bool:
    """
    Check if a query requires conversation history condensation based on referential terms or brevity.
    """
    cleaned = query.strip().lower()
    words = [
        w.strip("!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~")
        for w in cleaned.split()
    ]
    words = [w for w in words if w]

    if len(words) <= 2:
        return True

    return any(word in REFERENTIAL_PATTERNS for word in words)


def _condense_query(query: str, history: list[dict]) -> str:
    """
    Rephrase follow-up questions into standalone search queries.
    """

    if not history or not _should_condense_query(query):
        return query

    chat_history = "\n".join(
        f"{msg['role']}: {msg['content']}"
        for msg in history[-5:]
    )

    prompt = f"""Given the following conversation history and a follow-up question, rephrase the follow-up question into a standalone search query.

Do not answer the question.

Conversation History:
{chat_history}

Follow-up Question:
{query}

Standalone Query:
"""

    try:
        response = get_chat_model().invoke(prompt)

        condensed = (
            response.content
            if isinstance(response.content, str)
            else str(response.content)
        )

        return condensed.strip()

    except Exception:
        return query


def _build_grounded_prompt(
    query: str,
    search_results: list[SearchResult],
    history: list[dict],
) -> str:

    context_blocks = []

    for index, result in enumerate(search_results, start=1):

        source = result.source_file or "unknown source"
        page = result.page if result.page is not None else "unknown page"

        context_blocks.append(
            f"[Source {index}: {source}, page {page}, score {result.score:.4f}]\n"
            f"{result.content}"
        )

    context = "\n\n".join(context_blocks)

    history_text = ""

    if history:
        history_text = (
            "Conversation history:\n"
            + "\n".join(
                f"{msg['role'].capitalize()}: {msg['content']}"
                for msg in history[-3:]
            )
            + "\n\n"
        )

    return f"""You are an Enterprise RAG Assistant.

Answer the user's question using ONLY the provided document context.

Guidelines:
- Never invent information.
- If the answer is not present in the documents, clearly say that the uploaded documents do not contain enough information.
- Format your response using Markdown.
- Use headings when appropriate.
- Use bullet points for lists.
- Use numbered lists for steps or procedures.
- Highlight important terms, dates, and numbers using bold text.
- Keep paragraphs short and easy to read.
- Cite supporting information inline using [Source X].

{history_text}
Document context:

{context}

Question:

{query}

Answer:
"""