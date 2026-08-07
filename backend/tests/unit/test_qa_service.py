from unittest.mock import MagicMock, patch

from services.qa_service import (
    answer_question,
    _condense_query,
    _build_grounded_prompt,
)
from services.vector_store import SearchResult


@patch("services.qa_service.semantic_search")
def test_answer_question_no_results(mock_search):
    mock_search.return_value = []

    result = answer_question("Leave policy")

    assert result.source_count == 0
    assert result.sources == []
    assert "could not find" in result.answer.lower()


@patch("services.qa_service.get_chat_model")
@patch("services.qa_service.semantic_search")
def test_answer_question_success(mock_search, mock_get_chat):

    mock_search.return_value = [
        SearchResult(
            content="Employees receive 20 days leave.",
            score=0.95,
            source_file="policy.pdf",
            page=2,
        )
    ]

    llm = MagicMock()
    llm.invoke.return_value.content = "Employees receive 20 days leave."

    mock_get_chat.return_value = llm

    result = answer_question("Leave policy")

    assert result.source_count == 1
    assert result.sources[0].source_file == "policy.pdf"
    assert "20 days" in result.answer


def test_condense_query_without_history():
    query = "What is leave policy?"
    assert _condense_query(query, []) == query


@patch("services.qa_service.get_chat_model")
def test_condense_query_with_history(mock_get_chat):

    llm = MagicMock()
    llm.invoke.return_value.content = "leave policy"

    mock_get_chat.return_value = llm

    history = [
        {
            "role": "user",
            "content": "Tell me about HR",
        }
    ]

    result = _condense_query("What about leave?", history)

    assert result == "leave policy"


def test_build_grounded_prompt():

    results = [
        SearchResult(
            content="Employees receive 20 days leave.",
            score=0.90,
            source_file="policy.pdf",
            page=2,
        )
    ]

    prompt = _build_grounded_prompt(
        "Leave policy",
        results,
        [],
    )

    assert "policy.pdf" in prompt
    assert "Leave policy" in prompt
    assert "Source 1" in prompt