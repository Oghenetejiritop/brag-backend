
"""
Unit tests for lazy chatbot RAG reconstruction.

These tests verify cache reuse, reconstruction, and failure
handling without making external AI requests.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.dependencies import RAGManager


def test_lazy_rag_reconstruction() -> None:
    """Validate chatbot RAG cache and reconstruction behavior."""
    user_id = str(uuid4())
    chatbot_id = str(uuid4())

    manager = RAGManager()

    with patch(
        "app.dependencies.RAGService"
    ) as rag_service_class:
        first_service = MagicMock()
        rag_service_class.return_value = first_service

        # First access reconstructs the chatbot.
        result = manager.get_or_reconstruct_chatbot(
            user_id=user_id,
            chatbot_id=chatbot_id,
        )

        assert result is first_service

        first_service.initialize_from_existing_store.assert_called_once_with(
            user_id=user_id,
            chatbot_id=chatbot_id,
        )

        print("PASS: Missing chatbot service reconstructed.")

        # Second access must reuse the cached instance.
        cached_result = manager.get_or_reconstruct_chatbot(
            user_id=user_id,
            chatbot_id=chatbot_id,
        )

        assert cached_result is first_service
        assert rag_service_class.call_count == 1

        print("PASS: Cached chatbot service reused.")

        # Simulate a new RAGManager after an application restart.
        restarted_manager = RAGManager()

        assert not restarted_manager.has_chatbot_service(
            user_id=user_id,
            chatbot_id=chatbot_id,
        )

        second_service = MagicMock()
        rag_service_class.return_value = second_service

        reconstructed_result = (
            restarted_manager.get_or_reconstruct_chatbot(
                user_id=user_id,
                chatbot_id=chatbot_id,
            )
        )

        assert reconstructed_result is second_service

        second_service.initialize_from_existing_store.assert_called_once_with(
            user_id=user_id,
            chatbot_id=chatbot_id,
        )

        assert rag_service_class.call_count == 2

        print("PASS: Fresh manager reconstructs chatbot.")

        # Failed reconstruction must not populate the cache.
        missing_chatbot_id = str(uuid4())

        failed_service = MagicMock()
        failed_service.initialize_from_existing_store.side_effect = (
            FileNotFoundError("No persisted vector store.")
        )

        rag_service_class.return_value = failed_service

        try:
            restarted_manager.get_or_reconstruct_chatbot(
                user_id=user_id,
                chatbot_id=missing_chatbot_id,
            )
        except FileNotFoundError:
            pass
        else:
            raise AssertionError(
                "Missing vector store was unexpectedly accepted."
            )

        assert not restarted_manager.has_chatbot_service(
            user_id=user_id,
            chatbot_id=missing_chatbot_id,
        )

        print("PASS: Failed reconstruction was not cached.")

    print("PASS: Lazy RAG reconstruction validated.")


if __name__ == "__main__":
    test_lazy_rag_reconstruction()
