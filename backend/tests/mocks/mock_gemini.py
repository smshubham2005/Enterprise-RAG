"""
Mock Gemini models for unit testing.
"""

from unittest.mock import MagicMock


class MockGeminiEmbeddings:
    """
    Mock embedding model.
    """

    EMBEDDING_SIZE = 768

    def embed_documents(self, texts):
        return [
            [0.5] * self.EMBEDDING_SIZE
            for _ in texts
        ]

    def embed_query(self, text):
        return [0.5] * self.EMBEDDING_SIZE


class MockGeminiChat:
    """
    Mock Gemini chat model.
    """

    def invoke(self, prompt):

        response = MagicMock()

        response.content = (
            "This is a mocked Gemini response."
        )

        return response