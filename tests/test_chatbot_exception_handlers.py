
"""
Tests for BRAG chatbot HTTP exception handlers.

Uses a standalone FastAPI application so these tests
do not access or modify the development database.
"""

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.chatbot_exception_handlers import (
    register_chatbot_exception_handlers,
)
from app.exceptions.chatbot_exceptions import (
    ChatbotNotFoundError,
    InactiveChatbotError,
    InactiveChatbotOwnerError,
    InvalidChatbotNameError,
)


@pytest.fixture
def client() -> TestClient:
    """Create an isolated application with exception handlers."""

    test_app = FastAPI()
    register_chatbot_exception_handlers(test_app)

    @test_app.get("/test/not-found")
    def raise_not_found() -> None:
        raise ChatbotNotFoundError("Internal database information")

    @test_app.get("/test/inactive")
    def raise_inactive() -> None:
        raise InactiveChatbotError("Internal service information")

    @test_app.get("/test/inactive-owner")
    def raise_inactive_owner() -> None:
        raise InactiveChatbotOwnerError("Internal user information")

    @test_app.get("/test/invalid-name")
    def raise_invalid_name() -> None:
        raise InvalidChatbotNameError("Sensitive internal details")

    return TestClient(test_app)


def test_chatbot_not_found(client: TestClient) -> None:
    response = client.get("/test/not-found")

    assert response.status_code == 404
    assert response.json() == {
        "detail": "Chatbot was not found."
    }


def test_inactive_chatbot(client: TestClient) -> None:
    response = client.get("/test/inactive")

    assert response.status_code == 409
    assert response.json() == {
        "detail": "Chatbot is inactive."
    }


def test_inactive_owner(client: TestClient) -> None:
    response = client.get("/test/inactive-owner")

    assert response.status_code == 401
    assert response.json() == {
        "detail": "Authentication is no longer valid."
    }
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_invalid_chatbot_name(client: TestClient) -> None:
    response = client.get("/test/invalid-name")

    assert response.status_code == 422
    assert response.json() == {
        "detail": "Chatbot name is invalid."
    }
    assert "Sensitive internal details" not in response.text
