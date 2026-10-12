
"""
Subprocess worker for persistent RAG restart validation.

Usage:
    python -m tests.rag_restart_worker create PATH
    python -m tests.rag_restart_worker restore PATH
"""

import sys
from pathlib import Path
from unittest.mock import patch

from langchain_core.documents import Document

from app.dependencies import RAGManager
from app.services.rag_service import RAGService
from app.services.vector_store_service import VectorStoreService
from tests.fakes import FakeEmbeddings


def create_store(directory: Path) -> None:
    """Create a persisted Chroma database in a child process."""
    service = VectorStoreService(
        persist_directory=str(directory),
        embeddings=FakeEmbeddings(),
    )

    service.create_vector_store(
        documents=[
            Document(
                page_content=(
                    "BRAG chatbot alpha contains the secret "
                    "test phrase persistent knowledge works."
                ),
                metadata={"source": "restart_test"},
            )
        ]
    )

    print("PASS: Child process created persistent vectors.")


def restore_store(directory: Path) -> None:
    """Restore a real vector store through a fresh RAGManager."""
    user_id = "11111111-1111-1111-1111-111111111111"
    chatbot_id = "22222222-2222-2222-2222-222222222222"

    original_constructor = VectorStoreService

    def make_vector_service(
        persist_directory: str,
    ) -> VectorStoreService:
        return original_constructor(
            persist_directory=persist_directory,
            embeddings=FakeEmbeddings(),
        )

    # Replace the workspace path only for this test.
    # Real Chroma loading and retriever construction still run.
    with (
        patch(
            "app.services.rag_service.VectorStoreService",
            side_effect=make_vector_service,
        ),
        patch(
            "app.services.rag_service.ChatOpenAI"
        ),
        patch(
            "app.services.rag_service.WorkspaceService"
        ) as workspace_class,
    ):
        workspace = workspace_class.return_value
        workspace.get_chatbot_vector_store_directory.return_value = (
            directory
        )

        manager = RAGManager()

        rag_service: RAGService = (
            manager.get_or_reconstruct_chatbot(
                user_id=user_id,
                chatbot_id=chatbot_id,
            )
        )

        assert rag_service._retriever is not None

        documents = rag_service._retriever.invoke(
            "persistent knowledge works"
        )

        assert documents
        assert any(
            "persistent knowledge works" in document.page_content
            for document in documents
        )

        print("PASS: Fresh process reconstructed RAG.")
        print("PASS: Persisted document retrieved.")
        print("PASS: Real Chroma restart validation completed.")


def main() -> None:
    """Execute the requested subprocess operation."""
    if len(sys.argv) != 3:
        raise SystemExit(
            "Usage: python -m tests.rag_restart_worker "
            "<create|restore> <directory>"
        )

    action = sys.argv[1]
    directory = Path(sys.argv[2])

    if action == "create":
        create_store(directory)
    elif action == "restore":
        restore_store(directory)
    else:
        raise SystemExit(f"Unknown action: {action}")


if __name__ == "__main__":
    main()
