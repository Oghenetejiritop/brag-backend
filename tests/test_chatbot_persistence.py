
"""
Phase 5.7.5: Chatbot vector-store persistence tests.

Tests multiple-document ingestion, persistence after cache
reconstruction, and isolation between chatbots.

Uses fake embeddings to avoid OpenAI API charges.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from langchain_core.documents import Document
from langchain_core.embeddings import FakeEmbeddings

from app.services.vector_store_service import VectorStoreService


def create_test_service(
    storage_root: Path,
    user_id: str,
    chatbot_id: str,
) -> VectorStoreService:
    """Create a vector-store service for one test chatbot."""

    directory = (
        storage_root
        / user_id
        / "chatbots"
        / chatbot_id
        / "vector_store"
    )

    return VectorStoreService(
        persist_directory=str(directory),
        embeddings=FakeEmbeddings(size=32),
    )


def read_document_contents(
    service: VectorStoreService,
) -> set[str]:
    """Return stored document contents after reconstruction."""

    store = service.load_vector_store()

    result = store._collection.get(
        include=["documents"]
    )

    return set(result["documents"] or [])


def run_tests() -> None:
    """Execute chatbot persistence and isolation tests."""

    user_a = str(uuid4())
    user_b = str(uuid4())

    chatbot_a = str(uuid4())
    chatbot_b = str(uuid4())
    chatbot_c = str(uuid4())

    with TemporaryDirectory(
        ignore_cleanup_errors=True
    ) as directory:

        storage_root = Path(directory)

        # --------------------------------------------
        # Test 1: Multiple documents for one chatbot
        # --------------------------------------------
        service_a = create_test_service(
            storage_root,
            user_a,
            chatbot_a,
        )

        first_content = (
            "BRAG supports persistent chatbot knowledge bases."
        )

        second_content = (
            "BRAG supports multiple documents per chatbot."
        )

        service_a.add_documents(
            [
                Document(
                    page_content=first_content,
                    metadata={"source": "first.txt"},
                )
            ]
        )

        service_a.add_documents(
            [
                Document(
                    page_content=second_content,
                    metadata={"source": "second.txt"},
                )
            ]
        )

        stored_a = read_document_contents(service_a)

        assert first_content in stored_a
        assert second_content in stored_a
        assert len(stored_a) == 2

        print("PASS: Multiple documents preserved.")

        # --------------------------------------------
        # Test 2: Reconstruct after cache reset
        # --------------------------------------------
        del service_a

        reconstructed_a = create_test_service(
            storage_root,
            user_a,
            chatbot_a,
        )

        reconstructed_contents = read_document_contents(
            reconstructed_a
        )

        assert first_content in reconstructed_contents
        assert second_content in reconstructed_contents

        print("PASS: Knowledge survived reconstruction.")

        # --------------------------------------------
        # Test 3: Chatbot isolation
        # --------------------------------------------
        service_b = create_test_service(
            storage_root,
            user_a,
            chatbot_b,
        )

        chatbot_b_content = (
            "This knowledge belongs only to chatbot B."
        )

        service_b.add_documents(
            [
                Document(
                    page_content=chatbot_b_content,
                    metadata={"source": "chatbot_b.txt"},
                )
            ]
        )

        stored_b = read_document_contents(service_b)

        assert chatbot_b_content in stored_b
        assert first_content not in stored_b
        assert second_content not in stored_b

        print("PASS: Same-user chatbots remain isolated.")

        # --------------------------------------------
        # Test 4: User isolation
        # --------------------------------------------
        service_c = create_test_service(
            storage_root,
            user_b,
            chatbot_c,
        )

        user_b_content = (
            "This knowledge belongs only to user B."
        )

        service_c.add_documents(
            [
                Document(
                    page_content=user_b_content,
                    metadata={"source": "user_b.txt"},
                )
            ]
        )

        stored_c = read_document_contents(service_c)

        assert user_b_content in stored_c
        assert first_content not in stored_c
        assert chatbot_b_content not in stored_c

        print("PASS: Different users remain isolated.")

        print(
            "PASS: Phase 5.7.5 persistence tests completed."
        )


if __name__ == "__main__":
    run_tests()
