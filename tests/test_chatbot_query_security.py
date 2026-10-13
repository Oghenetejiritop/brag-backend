
"""
Phase 5.8.2: Chatbot query authorization tests.

Verify that:
- Unauthenticated requests are rejected.
- Users cannot query another user's chatbot.
- Inactive chatbots cannot be queried.
- Authorized requests use the correct tenant IDs.
- Rejected requests never reach the RAG service.

No OpenAI calls or real vector databases are needed.
"""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_authenticated_user
from app.api.chatbot_routes import get_chatbot_service
from app.exceptions.chatbot_exceptions import (
    ChatbotNotFoundError,
    InactiveChatbotError,
)


USER_A_ID = str(uuid4())
USER_B_ID = str(uuid4())

CHATBOT_A_ID = str(uuid4())
CHATBOT_B_ID = str(uuid4())


class FakeChatbotService:
    """Simulate ownership and active-status checks."""

    def get_chatbot(
        self,
        user,
        public_chatbot_id: str,
        require_active: bool = True,
    ):
        if (
            user.user_id == USER_A_ID
            and public_chatbot_id == CHATBOT_A_ID
        ):
            return SimpleNamespace(
                chatbot_id=CHATBOT_A_ID,
                is_active=True,
            )

        if (
            user.user_id == USER_B_ID
            and public_chatbot_id == CHATBOT_B_ID
        ):
            raise InactiveChatbotError(
                "Chatbot is inactive."
            )

        raise ChatbotNotFoundError(
            "Chatbot was not found."
        )


class FakeRAGService:
    """Return a predictable answer without calling an LLM."""

    def __init__(self) -> None:
        self.questions: list[str] = []

    def answer_question(self, question: str) -> str:
        self.questions.append(question)
        return "This is a simulated BRAG answer."


def run_tests() -> None:
    """Execute chatbot query security tests."""

    rag_service = FakeRAGService()
    reconstruction_calls: list[tuple[str, str]] = []

    def fake_reconstruction(
        user_id: str,
        chatbot_id: str,
    ) -> FakeRAGService:
        reconstruction_calls.append(
            (user_id, chatbot_id)
        )
        return rag_service

    def authenticate_user_a():
        return SimpleNamespace(
            user_id=USER_A_ID,
            is_active=True,
        )

    def authenticate_user_b():
        return SimpleNamespace(
            user_id=USER_B_ID,
            is_active=True,
        )

    def override_chatbot_service():
        return FakeChatbotService()

    def query_chatbot(
        client: TestClient,
        chatbot_id: str,
    ):
        return client.post(
            f"/api/v1/chatbots/{chatbot_id}/query",
            json={
                "question": "What does BRAG support?"
            },
        )

    original_overrides = dict(
        app.dependency_overrides
    )

    try:
        app.dependency_overrides.clear()

        app.dependency_overrides[
            get_chatbot_service
        ] = override_chatbot_service

        with patch(
            "app.api.chatbot_routes."
            "rag_manager.get_or_reconstruct_chatbot",
            side_effect=fake_reconstruction,
        ):
            with TestClient(app) as client:

                # Test 1: Missing authentication
                response = query_chatbot(
                    client,
                    CHATBOT_A_ID,
                )

                assert response.status_code == 401, (
                    response.text
                )

                assert reconstruction_calls == []
                assert rag_service.questions == []

                print(
                    "PASS: Unauthenticated query rejected."
                )

                # Test 2: Cross-user access
                app.dependency_overrides[
                    get_authenticated_user
                ] = authenticate_user_a

                response = query_chatbot(
                    client,
                    CHATBOT_B_ID,
                )

                assert response.status_code == 404, (
                    response.text
                )

                assert reconstruction_calls == []
                assert rag_service.questions == []

                print(
                    "PASS: Cross-user query rejected."
                )

                # Test 3: Inactive chatbot
                app.dependency_overrides[
                    get_authenticated_user
                ] = authenticate_user_b

                response = query_chatbot(
                    client,
                    CHATBOT_B_ID,
                )

                assert response.status_code == 409, (
                    response.text
                )

                assert reconstruction_calls == []
                assert rag_service.questions == []

                print(
                    "PASS: Inactive chatbot query rejected."
                )

                # Test 4: Authorized query
                app.dependency_overrides[
                    get_authenticated_user
                ] = authenticate_user_a

                response = query_chatbot(
                    client,
                    CHATBOT_A_ID,
                )

                assert response.status_code == 200, (
                    response.text
                )

                assert reconstruction_calls == [
                    (USER_A_ID, CHATBOT_A_ID)
                ]

                assert rag_service.questions == [
                    "What does BRAG support?"
                ]

                response_data = response.json()

                assert (
                    response_data["chatbot_id"]
                    == CHATBOT_A_ID
                )

                assert response_data["answer"] == (
                    "This is a simulated BRAG answer."
                )

                print(
                    "PASS: Authorized query returned answer."
                )

                # Test 5: No unauthorized RAG calls
                assert len(reconstruction_calls) == 1
                assert len(rag_service.questions) == 1

                print(
                    "PASS: Rejected queries caused "
                    "no RAG calls."
                )

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(
            original_overrides
        )


if __name__ == "__main__":
    run_tests()
    print(
        "PASS: Phase 5.8.2 security tests completed."
    )
