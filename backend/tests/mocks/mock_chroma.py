"""
Mock Chroma vector store.
"""

from langchain_core.documents import Document


class MockVectorStore:

    def __init__(self):

        self.documents = []

    def add_documents(self, documents):

        self.documents.extend(documents)

        return [
            f"doc_{i}"
            for i in range(len(documents))
        ]

    def similarity_search(self, query, k=4):

        return self.documents[:k]

    def similarity_search_with_score(self, query, k=4):

        results = []

        for i, doc in enumerate(self.documents[:k]):

            results.append(
                (
                    doc,
                    round(0.1 + (i * 0.05), 2),
                )
            )

        return results

    def delete(self):

        self.documents.clear()

    def count(self):

        return len(self.documents)

    def as_retriever(self):

        return self