
"""
RAG isolation tests for BRAG.

These tests verify that users receive independent RAG service
instances and independent vector-store persistence locations.

External OpenAI and Chroma operations are replaced with test
doubles so the isolation tests remain fast, deterministic,
and free of API costs.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import app.dependencies as dependencies_module
import app.services.rag_service as rag_service_module
from app.dependencies import RAGManager
from app.services.rag_service import RAGService


class FakeRAGService:
    """
    Minimal test double for RAGService.

    It records the user and file supplied during initialization
    without creating embeddings, vector stores, or LLM clients.
    """

    def __init__(self) -> None:
        self.file_path: str | None = None
        self.user_id: str | None = None

    def initialize_from_file(
        self,
        file_path: str,
        user_id: str,
    ) -> None:
        """
        Record initialization arguments for isolation testing.
        """

        self.file_path = file_path
        self.user_id = user_id


class FakeVectorStoreService:
    """
    Test double that records vector-store persistence paths.
    """

    persist_directories: list[str] = []

    def __init__(
        self,
        persist_directory: str,
    ) -> None:
        normalized_directory = str(
            persist_directory
        )

        self.persist_directories.append(
            normalized_directory
        )

    def create_vector_store(
        self,
        documents: list,
    ) -> object:
        """
        Return a harmless stand-in for a Chroma vector store.
        """

        return object()

    def create_retriever(
        self,
        vector_store: object,
    ) -> object:
        """
        Return a harmless stand-in for a LangChain retriever.
        """

        return object()


def test_rag_manager_isolates_users() -> None:
    """
    Verify that RAGManager stores a different RAG service
    instance for every user.
    """

    user_a_id = (
        "11111111-1111-1111-1111-111111111111"
    )

    user_b_id = (
        "22222222-2222-2222-2222-222222222222"
    )

    with patch.object(
        dependencies_module,
        "RAGService",
        FakeRAGService,
    ):
        rag_manager = RAGManager()

        rag_manager.initialize_from_file(
            file_path="user_a.pdf",
            user_id=user_a_id,
        )

        rag_manager.initialize_from_file(
            file_path="user_b.pdf",
            user_id=user_b_id,
        )

        user_a_service = rag_manager.get_service(
            user_a_id
        )

        user_b_service = rag_manager.get_service(
            user_b_id
        )

        # ---------------------------------------------------------
        # Each user must own a different RAGService object.
        # ---------------------------------------------------------
        assert (
            user_a_service
            is not user_b_service
        )

        # ---------------------------------------------------------
        # Each service must have been initialized for the
        # correct owner.
        # ---------------------------------------------------------
        assert (
            user_a_service.user_id
            == user_a_id
        )

        assert (
            user_b_service.user_id
            == user_b_id
        )

        assert (
            user_a_service.file_path
            == "user_a.pdf"
        )

        assert (
            user_b_service.file_path
            == "user_b.pdf"
        )

        # ---------------------------------------------------------
        # RAGManager must recognize both users independently.
        # ---------------------------------------------------------
        assert rag_manager.has_service(
            user_a_id
        )

        assert rag_manager.has_service(
            user_b_id
        )

        print(
            "PASS: User A and User B have "
            "separate RAGService instances."
        )


def test_vector_store_paths_are_isolated() -> None:
    """
    Verify that RAGService configures a separate vector-store
    persistence directory for every user.
    """

    user_a_id = (
        "11111111-1111-1111-1111-111111111111"
    )

    user_b_id = (
        "22222222-2222-2222-2222-222222222222"
    )

    FakeVectorStoreService.persist_directories.clear()

    with TemporaryDirectory() as temporary_directory:
        storage_root = Path(
            temporary_directory
        )

        document_a = (
            storage_root / "user_a.pdf"
        )

        document_b = (
            storage_root / "user_b.pdf"
        )

        # ---------------------------------------------------------
        # RAGService checks that the files physically exist before
        # delegating document loading, so create harmless placeholders.
        # ---------------------------------------------------------
        document_a.write_bytes(b"test")
        document_b.write_bytes(b"test")

        workspace_service = MagicMock()

        workspace_service.get_vector_store_directory.side_effect = (
            lambda user_id: (
                storage_root
                / user_id
                / "vector_store"
            )
        )

        document_service = MagicMock()

        document_service.load_and_split.return_value = [
            object()
        ]

        # ---------------------------------------------------------
        # Prevent this isolation test from creating real OpenAI
        # clients, embeddings, Chroma databases, or LCEL chains.
        # ---------------------------------------------------------
        with (
            patch.object(
                rag_service_module,
                "WorkspaceService",
                return_value=workspace_service,
            ),
            patch.object(
                rag_service_module,
                "DocumentService",
                return_value=document_service,
            ),
            patch.object(
                rag_service_module,
                "VectorStoreService",
                FakeVectorStoreService,
            ),
            patch.object(
                rag_service_module,
                "ChatOpenAI",
                return_value=MagicMock(),
            ),
            patch.object(
                RAGService,
                "_build_chain",
                return_value=MagicMock(),
            ),
        ):
            user_a_service = RAGService()
            user_b_service = RAGService()

            user_a_service.initialize_from_file(
                file_path=str(document_a),
                user_id=user_a_id,
            )

            user_b_service.initialize_from_file(
                file_path=str(document_b),
                user_id=user_b_id,
            )

        assert (
            len(
                FakeVectorStoreService.persist_directories
            )
            == 2
        )

        user_a_vector_directory = (
            FakeVectorStoreService.persist_directories[0]
        )

        user_b_vector_directory = (
            FakeVectorStoreService.persist_directories[1]
        )

        # ---------------------------------------------------------
        # The two vector databases must never point at the same
        # persistence location.
        # ---------------------------------------------------------
        assert (
            user_a_vector_directory
            != user_b_vector_directory
        )

        assert (
            Path(user_a_vector_directory)
            == storage_root
            / user_a_id
            / "vector_store"
        )

        assert (
            Path(user_b_vector_directory)
            == storage_root
            / user_b_id
            / "vector_store"
        )

        print(
            "PASS: User A vector-store path:",
            user_a_vector_directory,
        )

        print(
            "PASS: User B vector-store path:",
            user_b_vector_directory,
        )

        print(
            "PASS: Vector-store persistence "
            "is isolated by user."
        )


def test_rag_isolation() -> None:
    """
    Run the complete offline RAG isolation validation.
    """

    test_rag_manager_isolates_users()
    test_vector_store_paths_are_isolated()

    print(
        "PASS: RAG and vector-store "
        "isolation validated."
    )


if __name__ == "__main__":
    test_rag_isolation()