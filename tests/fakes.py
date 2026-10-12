
"""
Reusable deterministic test dependencies for BRAG.

These fake embeddings must never be used for production
semantic retrieval.
"""

from langchain_core.embeddings import Embeddings


class FakeEmbeddings(Embeddings):
    """Generate deterministic local vectors for tests."""

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Embed document text without external API calls."""
        return [self._embed_text(text) for text in texts]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        """Embed a query without external API calls."""
        return self._embed_text(text)

    @staticmethod
    def _embed_text(text: str) -> list[float]:
        """Return a stable, nonzero four-dimensional vector."""
        return [
            float(len(text) + 1),
            float(sum(ord(char) for char in text) % 997 + 1),
            float(sum(char.isalpha() for char in text) + 1),
            1.0,
        ]
