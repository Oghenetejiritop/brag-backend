
"""Isolated browser assistant integration tests; never use development brag.db."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.browser_auth_routes import (
    _rate_limit_attempts,
    _rate_limit_lock,
)
from app.db.database import Base, get_database_session
from app.db.models.api_key import APIKey  # noqa: F401
from app.db.models.browser_session import BrowserSession  # noqa: F401
from app.db.models.chatbot import Chatbot  # noqa: F401
from app.db.models.user import User  # noqa: F401
from app.main import app

ORIGIN = "http://testserver"
PASSWORD = "Correct-Password-2026!"


def reset_auth_rate_limits():
    """Reset process-local authentication counters for test isolation."""
    with _rate_limit_lock:
        _rate_limit_attempts.clear()


@pytest.fixture
def client():
    reset_auth_rate_limits()

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    def override_database():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_database_session] = override_database

    try:
        with TestClient(app, base_url=ORIGIN) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        engine.dispose()
        reset_auth_rate_limits()


def sign_in(client, email):
    register = client.post(
        "/api/v1/auth/register",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": PASSWORD},
    )
    assert register.status_code == 201, register.text

    login = client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text

    return login.json()["csrf_token"]


def create_assistant(
    client,
    token,
    name="Research assistant",
    origin=ORIGIN,
):
    return client.post(
        "/api/v1/browser/chatbots",
        headers={
            "Origin": origin,
            "X-CSRF-Token": token,
        },
        json={
            "name": name,
            "description": "Private research",
        },
    )


def test_anonymous_list_rejected(client):
    response = client.get("/api/v1/browser/chatbots")
    assert response.status_code == 401


def test_anonymous_create_rejected(client):
    result = create_assistant(client, "invalid")
    assert result.status_code == 401


def test_create_and_list_assistant(client):
    token = sign_in(client, "first@example.com")

    created = create_assistant(client, token)
    assert created.status_code == 201, created.text
    assert created.json()["name"] == "Research assistant"

    listed = client.get("/api/v1/browser/chatbots")
    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert (
        listed.json()[0]["chatbot_id"]
        == created.json()["chatbot_id"]
    )


def test_create_requires_csrf(client):
    sign_in(client, "first@example.com")

    result = create_assistant(client, "wrong-token")
    assert result.status_code == 403

    listed = client.get("/api/v1/browser/chatbots")
    assert listed.status_code == 200
    assert listed.json() == []


def test_cross_origin_create_rejected(client):
    token = sign_in(client, "first@example.com")

    result = create_assistant(
        client,
        token,
        origin="https://evil.example",
    )
    assert result.status_code == 403


def test_api_key_endpoint_still_requires_api_key(client):
    sign_in(client, "first@example.com")

    response = client.get("/api/v1/chatbots")
    assert response.status_code == 401


def test_tenant_isolation(client):
    token_a = sign_in(client, "first@example.com")

    created = create_assistant(client, token_a)
    assert created.status_code == 201

    logout = client.post(
        "/api/v1/auth/logout",
        headers={
            "Origin": ORIGIN,
            "X-CSRF-Token": token_a,
        },
    )
    assert logout.status_code == 204

    sign_in(client, "second@example.com")

    listed = client.get("/api/v1/browser/chatbots")
    assert listed.status_code == 200
    assert listed.json() == []
