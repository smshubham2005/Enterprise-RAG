"""
Shared sample documents and chat history used across tests.
"""

from langchain_core.documents import Document


def sample_documents_data():
    return [
        Document(
            page_content="Returns are accepted within 30 days of purchase.",
            metadata={
                "source_file": "policy.pdf",
                "page": 1,
                "total_pages": 10,
            },
        ),
        Document(
            page_content="Refund processing takes 5-7 business days.",
            metadata={
                "source_file": "policy.pdf",
                "page": 2,
                "total_pages": 10,
            },
        ),
        Document(
            page_content="Contact support@example.com for refund inquiries.",
            metadata={
                "source_file": "policy.pdf",
                "page": 3,
                "total_pages": 10,
            },
        ),
    ]


def sample_chunks_data():
    return [
        Document(
            page_content="Returns are accepted within 30 days.",
            metadata={
                "source_file": "policy.pdf",
                "page": 1,
                "chunk_id": "policy_p1_c0",
            },
        ),
        Document(
            page_content="Customers must provide original receipt.",
            metadata={
                "source_file": "policy.pdf",
                "page": 1,
                "chunk_id": "policy_p1_c1",
            },
        ),
        Document(
            page_content="Refund processing takes 5-7 business days.",
            metadata={
                "source_file": "policy.pdf",
                "page": 2,
                "chunk_id": "policy_p2_c0",
            },
        ),
    ]


def sample_chat_history():
    return [
        {
            "role": "user",
            "content": "What is your return policy?",
        },
        {
            "role": "assistant",
            "content": "Returns are accepted within 30 days.",
        },
        {
            "role": "user",
            "content": "How long do refunds take?",
        },
    ]