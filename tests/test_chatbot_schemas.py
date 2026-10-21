
"""
Tests for BRAG chatbot request and response schemas.
"""

from datetime import datetime, timezone
from uuid import uuid4

from pydantic import ValidationError

from app.api.chatbot_schemas import (
    ChatbotCreateRequest,
    ChatbotResponse,
)


def test_chatbot_schemas() -> None:
    """Validate chatbot API schemas and public fields."""
    request = ChatbotCreateRequest(
        name="Python Tutor",
        description="Answers Python questions.",
    )

    assert request.name == "Python Tutor"

    print("PASS: Valid chatbot creation request accepted.")

    try:
        ChatbotCreateRequest(name="")
    except ValidationError:
        pass
    else:
        raise AssertionError(
            "An empty chatbot name was accepted."
        )

    print("PASS: Empty chatbot name rejected.")

    try:
        ChatbotCreateRequest(name="A" * 101)
    except ValidationError:
        pass
    else:
        raise AssertionError(
            "An oversized chatbot name was accepted."
        )

    print("PASS: Oversized chatbot name rejected.")

    now = datetime.now(timezone.utc)

    response = ChatbotResponse(
        chatbot_id=str(uuid4()),
        name="Python Tutor",
        description=None,
        is_active=True,
        is_published=False,
        created_at=now,
        updated_at=now,
    )

    response_data = response.model_dump()

    assert "chatbot_id" in response_data
    assert response_data["is_published"] is False
    assert "id" not in response_data
    assert "user_id" not in response_data

    print("PASS: Internal database identifiers excluded.")
    print("PASS: Chatbot schema validation completed.")


if __name__ == "__main__":
    test_chatbot_schemas()
