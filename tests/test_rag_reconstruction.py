
"""
Unit tests for rebuilding a BRAG RAG pipeline.

Mocks replace external AI and vector-store operations so
this test requires no API calls or persistent Chroma files.
"""

from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.services.rag_service import RAGService


def test_rag_reconstruction() -> None:
    """Verify a RAG pipeline can be rebuilt from a saved store."""
    user_id = str(uuid4())
    chatbot_id = str(uuid4())

    with TemporaryDirectory() as temporary_directory:
        with (
            patch(
                "app.services.rag_service.WorkspaceService"
            ) as workspace_class,
            patch(
                "app.services.rag_service.VectorStoreService"
            ) as vector_store_class,
            patch(
                "app.services.rag_service.ChatOpenAI"
            ),
        ):
            workspace = workspace_class.return_value
            workspace.get_chatbot_vector_store_directory.return_value = (
                temporary_directory
            )

            vector_service = vector_store_class.return_value
            saved_store = MagicMock()
            retriever = MagicMock()

            vector_service.load_vector_store.return_value = saved_store
            vector_service.create_retriever.return_value = retriever

            service = RAGService()

            # Keep this unit test independent of the real LLM
            # and retriever execution.
            expected_chain = MagicMock()
            expected_chain.invoke.return_value = "Test answer"

            with patch.object(
                service,
                "_build_chain",
                return_value=expected_chain,
            ) as build_chain:
                service.initialize_from_existing_store(
                    user_id=user_id,
                    chatbot_id=chatbot_id,
                )

            workspace.get_chatbot_vector_store_directory.assert_called_once_with(
                user_id=user_id,
                chatbot_id=chatbot_id,
            )

            vector_service.load_vector_store.assert_called_once_with()
            vector_service.create_retriever.assert_called_once_with(
                saved_store
            )
            build_chain.assert_called_once_with()

            assert service._vector_store is saved_store
            assert service._retriever is retriever

            print("PASS: Persisted vector store was loaded.")
            print("PASS: Retriever was reconstructed.")
            print("PASS: RAG chain was reconstructed.")

            answer = service.answer_question("What is BRAG?")
            assert answer == "Test answer"

            expected_chain.invoke.assert_called_once_with(
                "What is BRAG?"
            )

            print("PASS: Reconstructed RAG service answered.")

            vector_service.create_vector_store.assert_not_called()

            print("PASS: Documents were not re-embedded.")
            print("PASS: RAG reconstruction unit test completed.")


if __name__ == "__main__":
    test_rag_reconstruction()
