
"""
Phase 5.7.4: Chatbot document-upload security tests.

Tests:
1. Missing authentication is rejected.
2. A user cannot upload to another user's chatbot.
3. Inactive chatbots reject uploads.
4. Authorized uploads use the correct user and chatbot IDs.
5. Rejected uploads never reach file storage or RAG ingestion.

No real API keys, embeddings, or database writes are required.
"""

from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_authenticated_user
from app.api.chatbot_routes import get_chatbot_service
from app.dependencies import rag_manager, upload_service
from app.exceptions.chatbot_exceptions import (
    ChatbotNotFoundError,
    InactiveChatbotError,
)


USER_A_ID = str(uuid4())
USER_B_ID = str(uuid4())

CHATBOT_A_ID = str(uuid4())
CHATBOT_B_ID = str(uuid4())


class FakeChatbotService:
    """Simulate chatbot ownership and active-status checks."""

    def get_chatbot(
        self,
        user,
        public_chatbot_id: str,
        require_active: bool = True,
    ):
        # User A owns an active chatbot.
        if (
            user.user_id == USER_A_ID
            and public_chatbot_id == CHATBOT_A_ID
        ):
            return SimpleNamespace(
                chatbot_id=CHATBOT_A_ID,
                is_active=True,
            )

        # User B owns an inactive chatbot.
        if (
            user.user_id == USER_B_ID
            and public_chatbot_id == CHATBOT_B_ID
        ):
            raise InactiveChatbotError(
                "Chatbot is inactive."
            )

        # Other combinations must be rejected.
        raise ChatbotNotFoundError(
            "Chatbot was not found."
        )


class FakeUploadService:
    """Record file-storage calls without writing to disk."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    async def save_chatbot_file(
        self,
        user_id: str,
        chatbot_id: str,
        file,
    ) -> str:
        self.calls.append((user_id, chatbot_id))
        return "fake-document.txt"


def run_tests() -> None:
    """Execute isolated HTTP security tests."""

    fake_upload = FakeUploadService()
    ingestion_calls: list[tuple[str, str]] = []

    original_save = upload_service.save_chatbot_file
    original_initialize = (
        rag_manager.initialize_chatbot_from_file
    )

    def fake_initialize(
        file_path: str,
        user_id: str,
        chatbot_id: str,
    ) -> None:
        ingestion_calls.append((user_id, chatbot_id))

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

    def upload_document(
        client: TestClient,
        chatbot_id: str,
    ):
        return client.post(
            f"/api/v1/chatbots/{chatbot_id}/documents",
            files={
                "file": (
                    "example.txt",
                    b"BRAG security test document",
                    "text/plain",
                )
            },
        )

    try:
        # Replace external side effects with test doubles.
        upload_service.save_chatbot_file = (
            fake_upload.save_chatbot_file
        )

        rag_manager.initialize_chatbot_from_file = (
            fake_initialize
        )

        app.dependency_overrides[get_chatbot_service] = (
            override_chatbot_service
        )

        with TestClient(app) as client:

            # --------------------------------------------
            # Test 1: Missing authentication
            # --------------------------------------------
            app.dependency_overrides.pop(
                get_authenticated_user,
                None,
            )

            response = upload_document(
                client,
                CHATBOT_A_ID,
            )

            assert response.status_code == 401, (
                f"Expected 401, got {response.status_code}: "
                f"{response.text}"
            )

            assert fake_upload.calls == []
            assert ingestion_calls == []

            print("PASS: Missing authentication rejected.")

            # --------------------------------------------
            # Test 2: Cross-user upload
            # --------------------------------------------
            app.dependency_overrides[
                get_authenticated_user
            ] = authenticate_user_a

            response = upload_document(
                client,
                CHATBOT_B_ID,
            )

            assert response.status_code == 404, (
                f"Expected 404, got {response.status_code}: "
                f"{response.text}"
            )

            assert fake_upload.calls == []
            assert ingestion_calls == []

            print("PASS: Cross-user upload rejected.")

            # --------------------------------------------
            # Test 3: Inactive chatbot
            # --------------------------------------------
            app.dependency_overrides[
                get_authenticated_user
            ] = authenticate_user_b

            response = upload_document(
                client,
                CHATBOT_B_ID,
            )

            assert response.status_code == 409, (
                f"Expected 409, got {response.status_code}: "
                f"{response.text}"
            )

            assert fake_upload.calls == []
            assert ingestion_calls == []

            print("PASS: Inactive chatbot upload rejected.")

            # --------------------------------------------
            # Test 4: Authorized upload
            # --------------------------------------------
            app.dependency_overrides[
                get_authenticated_user
            ] = authenticate_user_a

            response = upload_document(
                client,
                CHATBOT_A_ID,
            )

            assert response.status_code == 201, (
                f"Expected 201, got {response.status_code}: "
                f"{response.text}"
            )

            assert fake_upload.calls == [
                (USER_A_ID, CHATBOT_A_ID)
            ]

            assert ingestion_calls == [
                (USER_A_ID, CHATBOT_A_ID)
            ]

            response_data = response.json()

            assert (
                response_data["chatbot_id"]
                == CHATBOT_A_ID
            )

            print("PASS: Authorized upload accepted.")

            # --------------------------------------------
            # Test 5: No unauthorized side effects
            # --------------------------------------------
            assert len(fake_upload.calls) == 1
            assert len(ingestion_calls) == 1

            print(
                "PASS: Rejected uploads caused "
                "no storage or ingestion calls."
            )

    finally:
        # Restore production services.
        upload_service.save_chatbot_file = original_save

        rag_manager.initialize_chatbot_from_file = (
            original_initialize
        )

        app.dependency_overrides.clear()


if __name__ == "__main__":
    run_tests()
    print(
        "PASS: Phase 5.7.4 security tests completed."
    )
