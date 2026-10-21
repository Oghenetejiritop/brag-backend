
"""
HTTP security tests for BRAG chatbot management.

Uses fake users and an in-memory chatbot service.
No production database, API keys, or Uvicorn required.
"""

from datetime import datetime, timezone
from types import SimpleNamespace
from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.api.dependencies import get_authenticated_user
from app.api.chatbot_routes import get_chatbot_service
from app.exceptions.chatbot_exceptions import (
    ChatbotNotFoundError,
    InactiveChatbotError,
)


class FakeChatbotService:
    """Simulate chatbot operations with owner-based access checks."""

    def __init__(self) -> None:
        self.chatbots = {}

    def create_chatbot(self, user, name, description=None):
        now = datetime.now(timezone.utc)

        chatbot = SimpleNamespace(
            chatbot_id=str(uuid4()),
            user_id=user.id,
            name=name.strip(),
            description=description,
            is_active=True,
            is_published=False,
            created_at=now,
            updated_at=now,
        )

        self.chatbots[chatbot.chatbot_id] = chatbot
        return chatbot

    def get_user_chatbots(self, user):
        return [
            chatbot
            for chatbot in self.chatbots.values()
            if chatbot.user_id == user.id
        ]

    def get_chatbot(
        self,
        user,
        public_chatbot_id,
        require_active=True,
    ):
        chatbot = self.chatbots.get(public_chatbot_id)

        if chatbot is None or chatbot.user_id != user.id:
            raise ChatbotNotFoundError(
                "Chatbot was not found."
            )

        if require_active and not chatbot.is_active:
            raise InactiveChatbotError(
                "Chatbot is inactive."
            )

        return chatbot

    def deactivate_chatbot(self, user, public_chatbot_id):
        chatbot = self.get_chatbot(
            user=user,
            public_chatbot_id=public_chatbot_id,
        )

        chatbot.is_active = False
        chatbot.updated_at = datetime.now(timezone.utc)

        return chatbot


def test_chatbot_api_security() -> None:
    """Test chatbot CRUD, authentication, and tenant isolation."""

    user_a = SimpleNamespace(id=1, is_active=True)
    user_b = SimpleNamespace(id=2, is_active=True)

    fake_service = FakeChatbotService()
    current_user = user_a

    def override_authenticated_user():
        return current_user

    def override_chatbot_service():
        return fake_service

    # Override only the dependencies used by the chatbot routes.
    app.dependency_overrides[get_authenticated_user] = (
        override_authenticated_user
    )
    app.dependency_overrides[get_chatbot_service] = (
        override_chatbot_service
    )

    try:
        with TestClient(app) as client:

            # User A creates a chatbot.
            response = client.post(
                "/api/v1/chatbots",
                json={
                    "name": "Private Knowledge Bot",
                    "description": "User A's documents",
                },
            )

            assert response.status_code == 201, (
                response.text
            )

            assert response.json()["is_published"] is False
            chatbot_id = response.json()["chatbot_id"]
            print("PASS: User A created a chatbot.")

            # User A can list their chatbot.
            response = client.get("/api/v1/chatbots")

            assert response.status_code == 200
            assert len(response.json()) == 1
            assert response.json()[0]["is_published"] is False
            print("PASS: User A can list their chatbot.")

            # User A can retrieve their chatbot.
            response = client.get(
                f"/api/v1/chatbots/{chatbot_id}"
            )

            assert response.status_code == 200
            assert response.json()["is_published"] is False
            print("PASS: User A can retrieve their chatbot.")

            # Switch the authenticated identity to User B.
            current_user = user_b

            # User B must not see User A's chatbot in a list.
            response = client.get("/api/v1/chatbots")

            assert response.status_code == 200
            assert response.json() == []
            print("PASS: User B cannot list User A's chatbot.")

            # User B must not retrieve User A's chatbot.
            response = client.get(
                f"/api/v1/chatbots/{chatbot_id}"
            )

            assert response.status_code == 404, (
                response.text
            )
            print("PASS: Cross-tenant retrieval rejected.")

            # User B must not deactivate User A's chatbot.
            response = client.patch(
                f"/api/v1/chatbots/{chatbot_id}/deactivate"
            )

            assert response.status_code == 404, (
                response.text
            )
            print("PASS: Cross-tenant deactivation rejected.")

            # Switch back to User A.
            current_user = user_a

            response = client.get(
                f"/api/v1/chatbots/{chatbot_id}"
            )

            assert response.status_code == 200
            assert response.json()["is_active"] is True
            assert response.json()["is_published"] is False
            print("PASS: Unauthorized attempt changed nothing.")

            # User A deactivates their chatbot.
            response = client.patch(
                f"/api/v1/chatbots/{chatbot_id}/deactivate"
            )

            assert response.status_code == 200, (
                response.text
            )
            assert response.json()["is_active"] is False
            print("PASS: Owner deactivated chatbot.")

            # Inactive chatbot must be rejected.
            response = client.get(
                f"/api/v1/chatbots/{chatbot_id}"
            )

            assert response.status_code == 409, (
                response.text
            )
            print("PASS: Inactive chatbot rejected.")

    finally:
        # Restore the original dependencies even if a test fails.
        app.dependency_overrides.pop(
            get_authenticated_user,
            None,
        )
        app.dependency_overrides.pop(
            get_chatbot_service,
            None,
        )

    print("\nPASS: Simulated chatbot API security tests.")


if __name__ == "__main__":
    test_chatbot_api_security()
