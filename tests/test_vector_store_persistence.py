import gc

"""
Persistence tests for BRAG's Chroma vector stores.

Tests use deterministic local embeddings and temporary
directories to avoid external API calls and production data.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

from app.services.vector_store_service import VectorStoreService


class FakeEmbeddings(Embeddings):
    """
    Provide deterministic embeddings for local persistence tests.

    These embeddings are for testing only and must not be used
    for production semantic retrieval.
    """

    def embed_documents(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """Generate local vectors for document chunks."""
        return [
            self._embed_text(text)
            for text in texts
        ]

    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        """Generate a local vector for a search query."""
        return self._embed_text(text)

    @staticmethod
    def _embed_text(text: str) -> list[float]:
        """
        Generate a fixed-length vector from text characters.

        The calculation is deterministic, so the same text
        receives the same vector across service instances.
        """
        values = [
            float(len(text) + 1),
            float(sum(ord(char) for char in text) % 997 + 1),
            float(sum(char.isalpha() for char in text) + 1),
            1.0,
        ]

        return values


def test_vector_store_persistence() -> None:
    """
    Verify Chroma can be reopened from persistent storage.
    """
    with TemporaryDirectory() as temporary_directory:
        storage_path = (
            Path(temporary_directory)
            / "chatbot_vector_store"
        )

        documents = [
            Document(
                page_content=(
                    "BRAG is a retrieval augmented "
                    "generation platform."
                ),
                metadata={"source": "test_document"},
            )
        ]

        # Create a persistent vector store.
        creator = VectorStoreService(
            persist_directory=str(storage_path)
        )
        creator._embeddings = FakeEmbeddings()

        created_store = creator.create_vector_store(
            documents=documents
        )

        assert created_store._collection.count() == 1

        print(
            "PASS: Persistent Chroma database created."
        )

        # Simulate a fresh service instance after a restart.
        loader = VectorStoreService(
            persist_directory=str(storage_path)
        )
        loader._embeddings = FakeEmbeddings()

        loaded_store = loader.load_vector_store()

        assert loaded_store._collection.count() == 1

        print(
            "PASS: Existing Chroma database reopened."
        )

        # Verify that saved document content is retrievable.
        results = loaded_store.similarity_search(
            "What is BRAG?",
            k=1,
        )

        assert len(results) == 1
        assert "BRAG" in results[0].page_content

        print(
            "PASS: Persisted document content retrieved."
        )

        # Missing databases must not be silently created.
        missing_path = (
            Path(temporary_directory)
            / "missing_vector_store"
        )

        missing_loader = VectorStoreService(
            persist_directory=str(missing_path)
        )
        missing_loader._embeddings = FakeEmbeddings()

        try:
            missing_loader.load_vector_store()
        except FileNotFoundError:
            pass
        else:
            raise AssertionError(
                "Missing Chroma database was accepted."
            )

        assert not missing_path.exists()

        print(
            "PASS: Missing vector database rejected."
        )

        # Release Chroma objects before Windows attempts to delete
        # the temporary vector database and its index files.
        del results
        del loaded_store
        del created_store
        del loader
        del creator
        del missing_loader

        gc.collect()
        print(
            "PASS: Vector store persistence validated."
        )


if __name__ == "__main__":
    test_vector_store_persistence()
