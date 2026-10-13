
"""
Phase 5.8.4: Chatbot query validation and error tests.

Verify:
1. Empty questions are rejected.
2. Whitespace-only questions are rejected.
3. Questions longer than 4000 characters are rejected.
4. Valid questions have surrounding whitespace removed.
5. Missing knowledge bases return HTTP 409.
6. Rejected requests never call the language model.
"""

from types import SimpleNamespace
from unittest.mock import patch
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.api.chatbot_routes import (
    get_authenticated_user,
    get_chatbot_service,
)


USER_ID = str(uuid4())
CHATBOT_ID = str(uuid4())

QUERY_URL = f"/api/v1/chatbots/{CHATBOT_ID}/query"


class FakeChatbotService:
    """Return an authorized, active chatbot."""

    def get_chatbot(
        self,
        user,
        public_chatbot_id: str,
        require_active: bool = True,
    ):
        assert str(user.user_id) == USER_ID
        assert public_chatbot_id == CHATBOT_ID

        return SimpleNamespace(
            chatbot_id=CHATBOT_ID,
            is_active=True,
        )


class FakeRAGService:
    """Record questions without invoking OpenAI."""

    def __init__(self) -> None:
        self.questions: list[str] = []

    def answer_question(self, question: str) -> str:
        self.questions.append(question)
        return "Simulated chatbot answer."


def run_tests() -> None:
    """Run all Phase 5.8.4 tests."""

    rag_service = FakeRAGService()
    reconstruction_calls: list[tuple[str, str]] = []

    def authenticate_user():
        return SimpleNamespace(
            user_id=USER_ID,
            is_active=True,
        )

    def override_chatbot_service():
        return FakeChatbotService()

    def reconstruct_chatbot(
        user_id: str,
        chatbot_id: str,
    ):
        reconstruction_calls.append(
            (user_id, chatbot_id)
        )
        return rag_service

    original_overrides = dict(
        app.dependency_overrides
    )

    try:
        app.dependency_overrides.clear()

        app.dependency_overrides[
            get_authenticated_user
        ] = authenticate_user

        app.dependency_overrides[
            get_chatbot_service
        ] = override_chatbot_service

        with patch(
            "app.api.chatbot_routes."
            "rag_manager.get_or_reconstruct_chatbot",
            side_effect=reconstruct_chatbot,
        ):
            with TestClient(app) as client:

                # Test 1: Empty question
                response = client.post(
                    QUERY_URL,
                    json={"question": ""},
                )

                assert response.status_code == 422, (
                    response.text
                )
                assert reconstruction_calls == []
                assert rag_service.questions == []

                print("PASS: Empty question rejected.")

                # Test 2: Whitespace-only question
                response = client.post(
                    QUERY_URL,
                    json={"question": "   "},
                )

                assert response.status_code == 422, (
                    response.text
                )
                assert reconstruction_calls == []
                assert rag_service.questions == []

                print(
                    "PASS: Whitespace-only question rejected."
                )

                # Test 3: Question exceeds 4000 characters
                response = client.post(
                    QUERY_URL,
                    json={"question": "A" * 4001},
                )

                assert response.status_code == 422, (
                    response.text
                )
                assert reconstruction_calls == []
                assert rag_service.questions == []

                print("PASS: Oversized question rejected.")

                # Test 4: Missing question field
                response = client.post(
                    QUERY_URL,
                    json={},
                )

                assert response.status_code == 422, (
                    response.text
                )
                assert reconstruction_calls == []
                assert rag_service.questions == []

                print("PASS: Missing question field rejected.")

                # Test 5: Valid question is normalized
                response = client.post(
                    QUERY_URL,
                    json={
                        "question": "  What is BRAG?  "
                    },
                )

                assert response.status_code == 200, (
                    response.text
                )

                assert reconstruction_calls == [
                    (USER_ID, CHATBOT_ID)
                ]

                assert rag_service.questions == [
                    "What is BRAG?"
                ]

                assert response.json() == {
                    "chatbot_id": CHATBOT_ID,
                    "answer": "Simulated chatbot answer.",
                }

                print(
                    "PASS: Valid question normalized "
                    "and answered."
                )

        # Test 6: Missing knowledge base
        with patch(
            "app.api.chatbot_routes."
            "rag_manager.get_or_reconstruct_chatbot",
            side_effect=FileNotFoundError(
                "Internal storage path is unavailable."
            ),
        ):
            with TestClient(app) as client:
                response = client.post(
                    QUERY_URL,
                    json={"question": "What is BRAG?"},
                )

                assert response.status_code == 409, (
                    response.text
                )

                assert (
                    "Upload a document first"
                    in response.json()["detail"]
                )

                # Internal filesystem details must not leak.
                assert (
                    "Internal storage path"
                    not in response.text
                )

                assert rag_service.questions == [
                    "What is BRAG?"
                ]

                print(
                    "PASS: Missing knowledge base "
                    "returns safe HTTP 409."
                )

    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(
            original_overrides
        )

    print(
        "PASS: Phase 5.8.4 validation tests completed."
    )


if __name__ == "__main__":
    run_tests()
