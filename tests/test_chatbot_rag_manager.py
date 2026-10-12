
"""
Unit tests for BRAG's chatbot-specific RAG manager.

Tests use mocks to avoid external AI calls and persistent
vector-store operations.
"""

from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.dependencies import RAGManager


def test_chatbot_rag_manager() -> None:
    """Verify chatbot cache isolation and reconstruction."""
    user_a = str(uuid4())
    user_b = str(uuid4())

    chatbot_a = str(uuid4())
    chatbot_b = str(uuid4())

    manager = RAGManager()

    assert not manager.has_chatbot_service(
        user_a,
        chatbot_a,
    )

    print("PASS: New chatbot has no cached RAG service.")

    with patch(
        "app.dependencies.RAGService"
    ) as rag_service_class:
        first_service = MagicMock()
        second_service = MagicMock()
        third_service = MagicMock()

        rag_service_class.side_effect = [
            first_service,
            second_service,
            third_service,
        ]

        # Reconstruct Chatbot A for User A.
        result_a = manager.reconstruct_chatbot(
            user_id=user_a,
            chatbot_id=chatbot_a,
        )

        assert result_a is first_service

        first_service.initialize_from_existing_store.assert_called_once_with(
            user_id=user_a,
            chatbot_id=chatbot_a,
        )

        print("PASS: Chatbot A reconstructed successfully.")

        # The second request should reuse the cached service.
        cached_result = manager.reconstruct_chatbot(
            user_id=user_a,
            chatbot_id=chatbot_a,
        )

        assert cached_result is first_service
        assert rag_service_class.call_count == 1

        print("PASS: Existing chatbot service reused.")

        # A different chatbot belonging to the same user
        # must receive its own RAGService instance.
        result_b = manager.reconstruct_chatbot(
            user_id=user_a,
            chatbot_id=chatbot_b,
        )

        assert result_b is second_service
        assert result_b is not result_a

        print("PASS: Same-user chatbots are isolated.")

        # The same chatbot UUID under a different user
        # must not reuse User A's cached service.
        result_other_user = manager.reconstruct_chatbot(
            user_id=user_b,
            chatbot_id=chatbot_a,
        )

        assert result_other_user is third_service
        assert result_other_user is not result_a

        print("PASS: Cross-user chatbot cache isolation validated.")

        assert manager.has_chatbot_service(
            user_a,
            chatbot_a,
        )

        assert manager.get_chatbot_service(
            user_a,
            chatbot_a,
        ) is first_service

        print("PASS: Chatbot cache lookup validated.")

        # A missing chatbot must not return another
        # chatbot's RAG service.
        try:
            manager.get_chatbot_service(
                user_id=user_b,
                chatbot_id=chatbot_b,
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                "Missing chatbot unexpectedly returned a service."
            )

        print("PASS: Missing chatbot cache lookup rejected.")

    print("PASS: Chatbot RAG manager validation completed.")


if __name__ == "__main__":
    test_chatbot_rag_manager()
