
"""
Test chatbot-specific persistent document ingestion.

Uses deterministic fake embeddings.
"""

import gc
from pathlib import Path
from tempfile import TemporaryDirectory

from langchain_core.documents import Document
from langchain_core.embeddings import FakeEmbeddings

from app.services.vector_store_service import VectorStoreService


def test_multiple_document_ingestion() -> None:
    with TemporaryDirectory() as directory:
        vector_store_directory = str(
            Path(directory) / "chatbot_vectors"
        )

        service = VectorStoreService(
            persist_directory=vector_store_directory,
            embeddings=FakeEmbeddings(size=32),
        )

        first_document = Document(
            page_content="BRAG supports private knowledge bases.",
            metadata={"source": "first.txt"},
        )

        second_document = Document(
            page_content="BRAG uses persistent Chroma vector stores.",
            metadata={"source": "second.txt"},
        )

        first_store = service.add_documents(
            [first_document]
        )

        assert first_store._collection.count() == 1
        print("PASS: First document ingested.")

        second_store = service.add_documents(
            [second_document]
        )

        assert second_store._collection.count() == 2
        print("PASS: Second document appended.")

        reconstructed_service = VectorStoreService(
            persist_directory=vector_store_directory,
            embeddings=FakeEmbeddings(size=32),
        )

        reconstructed_store = (
            reconstructed_service.load_vector_store()
        )

        assert reconstructed_store._collection.count() == 2

        stored_documents = (
            reconstructed_store._collection.get(
                include=["documents"]
            )["documents"]
        )

        assert first_document.page_content in stored_documents
        assert second_document.page_content in stored_documents
        # Release references to Chroma before deleting temporary files.
        del first_store
        del second_store
        del reconstructed_store
        del service
        del reconstructed_service

        gc.collect()

        print("PASS: Both documents survived reconstruction.")


if __name__ == "__main__":
    test_multiple_document_ingestion()
    print("PASS: Chatbot ingestion tests completed.")
