
"""
Phase 5.8.3: Persistent chatbot RAG reconstruction tests.

Tests the RAGManager cache and reconstruction behavior.

Uses a fake RAGService so no OpenAI calls or real Chroma
databases are required.
"""

from unittest.mock import patch
from uuid import uuid4

from app.dependencies import RAGManager


class FakeRAGService:
    """Simulate a RAG service backed by persistent storage."""

    # Records every reconstruction attempt.
    reconstruction_calls: list[tuple[str, str]] = []

    # Simulated persisted knowledge bases.
    persisted_knowledge: dict[tuple[str, str], str] = {}

    def __init__(self) -> None:
        self.user_id: str | None = None
        self.chatbot_id: str | None = None
        self.knowledge: str | None = None

    def initialize_from_existing_store(
        self,
        user_id: str,
        chatbot_id: str,
    ) -> None:
        """Simulate loading a chatbot's saved knowledge base."""

        key = (user_id, chatbot_id)

        self.reconstruction_calls.append(key)

        if key not in self.persisted_knowledge:
            raise FileNotFoundError(
                "No persisted chatbot knowledge base exists."
            )

        self.user_id = user_id
        self.chatbot_id = chatbot_id
        self.knowledge = self.persisted_knowledge[key]

    def answer_question(self, question: str) -> str:
        """Return a predictable answer using loaded knowledge."""

        if self.knowledge is None:
            raise ValueError(
                "RAG service has not been initialized."
            )

        return f"{self.knowledge} | Question: {question}"


def run_tests() -> None:
    """Run chatbot reconstruction tests."""

    user_a = str(uuid4())
    user_b = str(uuid4())

    chatbot_a = str(uuid4())
    chatbot_b = str(uuid4())
    chatbot_c = str(uuid4())
    missing_chatbot = str(uuid4())

    FakeRAGService.reconstruction_calls.clear()

    FakeRAGService.persisted_knowledge = {
        (user_a, chatbot_a): "Knowledge for chatbot A",
        (user_a, chatbot_b): "Knowledge for chatbot B",
        (user_b, chatbot_c): "Knowledge for user B",
    }

    # Replace only the RAGService constructor used by RAGManager.
    with patch(
        "app.dependencies.RAGService",
        FakeRAGService,
    ):
        manager = RAGManager()

        # --------------------------------------------
        # Test 1: Reconstruct an uncached chatbot
        # --------------------------------------------
        assert not manager.has_chatbot_service(
            user_id=user_a,
            chatbot_id=chatbot_a,
        )

        service_a = manager.get_or_reconstruct_chatbot(
            user_id=user_a,
            chatbot_id=chatbot_a,
        )

        answer = service_a.answer_question(
            "What does this chatbot know?"
        )

        assert "Knowledge for chatbot A" in answer

        assert manager.has_chatbot_service(
            user_id=user_a,
            chatbot_id=chatbot_a,
        )

        assert FakeRAGService.reconstruction_calls.count(
            (user_a, chatbot_a)
        ) == 1

        print("PASS: Uncached chatbot reconstructed.")

        # --------------------------------------------
        # Test 2: Cached service is reused
        # --------------------------------------------
        cached_service = manager.get_or_reconstruct_chatbot(
            user_id=user_a,
            chatbot_id=chatbot_a,
        )

        assert cached_service is service_a

        assert FakeRAGService.reconstruction_calls.count(
            (user_a, chatbot_a)
        ) == 1

        print("PASS: Cached chatbot service reused.")

        # --------------------------------------------
        # Test 3: Simulate application restart
        # --------------------------------------------
        # A new manager has an empty in-memory cache.
        # The simulated persisted knowledge remains available.
        restarted_manager = RAGManager()

        assert not restarted_manager.has_chatbot_service(
            user_id=user_a,
            chatbot_id=chatbot_a,
        )

        restored_service = (
            restarted_manager.get_or_reconstruct_chatbot(
                user_id=user_a,
                chatbot_id=chatbot_a,
            )
        )

        assert restored_service is not service_a

        restored_answer = restored_service.answer_question(
            "Can you still answer?"
        )

        assert "Knowledge for chatbot A" in restored_answer

        assert FakeRAGService.reconstruction_calls.count(
            (user_a, chatbot_a)
        ) == 2

        print("PASS: Chatbot reconstructed after cache reset.")

        # --------------------------------------------
        # Test 4: Separate chatbot knowledge
        # --------------------------------------------
        service_b = (
            restarted_manager.get_or_reconstruct_chatbot(
                user_id=user_a,
                chatbot_id=chatbot_b,
            )
        )

        answer_b = service_b.answer_question(
            "What do you know?"
        )

        assert "Knowledge for chatbot B" in answer_b
        assert "Knowledge for chatbot A" not in answer_b

        assert service_b is not restored_service

        print("PASS: Different chatbots use separate services.")

        # --------------------------------------------
        # Test 5: Separate users
        # --------------------------------------------
        service_c = (
            restarted_manager.get_or_reconstruct_chatbot(
                user_id=user_b,
                chatbot_id=chatbot_c,
            )
        )

        answer_c = service_c.answer_question(
            "What do you know?"
        )

        assert "Knowledge for user B" in answer_c
        assert "Knowledge for chatbot A" not in answer_c

        print("PASS: User-specific RAG caches remain isolated.")

        # --------------------------------------------
        # Test 6: Missing knowledge base
        # --------------------------------------------
        try:
            restarted_manager.get_or_reconstruct_chatbot(
                user_id=user_a,
                chatbot_id=missing_chatbot,
            )

        except FileNotFoundError:
            pass

        else:
            raise AssertionError(
                "Missing knowledge base should raise "
                "FileNotFoundError."
            )

        assert not restarted_manager.has_chatbot_service(
            user_id=user_a,
            chatbot_id=missing_chatbot,
        )

        print("PASS: Failed reconstruction was not cached.")

    print(
        "PASS: Phase 5.8.3 reconstruction tests completed."
    )


if __name__ == "__main__":
    run_tests()
