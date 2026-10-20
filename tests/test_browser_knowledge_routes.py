"""Browser knowledge API tests with isolated database and mocked RAG services."""

from io import BytesIO
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api import browser_auth_routes
from app.db.database import Base, get_database_session
from app.db.models.api_key import APIKey  # noqa: F401
from app.db.models.browser_session import BrowserSession  # noqa: F401
from app.db.models.chatbot import Chatbot  # noqa: F401
from app.db.models.user import User  # noqa: F401
from app.main import app

ORIGIN = "http://testserver"
PASSWORD = "Correct-Password-2026!"


@pytest.fixture
def client():
    """Give each test an isolated SQLite database and fresh auth counters."""
    with browser_auth_routes._rate_limit_lock:
        browser_auth_routes._rate_limit_attempts.clear()

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
        with browser_auth_routes._rate_limit_lock:
            browser_auth_routes._rate_limit_attempts.clear()


def sign_in(client, email):
    registered = client.post(
        "/api/v1/auth/register",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": PASSWORD},
    )
    assert registered.status_code == 201, registered.text

    login = client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": PASSWORD},
    )
    assert login.status_code == 200, login.text
    return login.json()["csrf_token"]


def create_assistant(client, token):
    response = client.post(
        "/api/v1/browser/chatbots",
        headers={"Origin": ORIGIN, "X-CSRF-Token": token},
        json={"name": "Research assistant"},
    )
    assert response.status_code == 201, response.text
    return response.json()["chatbot_id"]


def upload(client, assistant_id, token, contents=b"%PDF-1.4\nexample"):
    return client.post(
        f"/api/v1/browser/chatbots/{assistant_id}/documents",
        headers={"Origin": ORIGIN, "X-CSRF-Token": token},
        files={"file": ("sample.pdf", BytesIO(contents), "application/pdf")},
    )


def question(client, assistant_id, token):
    return client.post(
        f"/api/v1/browser/chatbots/{assistant_id}/query",
        headers={"Origin": ORIGIN, "X-CSRF-Token": token},
        json={"question": "What does the document say?"},
    )


def test_anonymous_upload_and_query_are_rejected(client):
    assert upload(client, "unknown", "invalid").status_code == 401
    assert question(client, "unknown", "invalid").status_code == 401


def test_upload_rejects_invalid_csrf(client):
    token = sign_in(client, "first@example.com")
    assistant_id = create_assistant(client, token)
    assert upload(client, assistant_id, "wrong").status_code == 403


def test_upload_rejects_non_pdf_contents(client):
    token = sign_in(client, "first@example.com")
    assistant_id = create_assistant(client, token)
    assert upload(client, assistant_id, token, b"not-a-pdf").status_code == 415


def test_query_requires_knowledge_base(client, monkeypatch):
    token = sign_in(client, "first@example.com")
    assistant_id = create_assistant(client, token)

    from app.api import browser_knowledge_routes

    monkeypatch.setattr(
        browser_knowledge_routes.rag_manager,
        "get_or_reconstruct_chatbot",
        Mock(side_effect=ValueError("no knowledge")),
    )
    assert question(client, assistant_id, token).status_code == 409


def test_upload_and_query_success(client, monkeypatch, tmp_path):
    token = sign_in(client, "first@example.com")
    assistant_id = create_assistant(client, token)

    from app.api import browser_knowledge_routes

    sample = tmp_path / "sample.pdf"
    sample.write_bytes(b"%PDF-1.4\nexample")
    save_mock = Mock(return_value=str(sample))

    async def fake_save_chatbot_file(**_kwargs):
        return save_mock()

    monkeypatch.setattr(
        browser_knowledge_routes.upload_service,
        "save_chatbot_file",
        fake_save_chatbot_file,
    )
    monkeypatch.setattr(
        browser_knowledge_routes.rag_manager,
        "initialize_chatbot_from_file",
        Mock(),
    )
    mock_rag = Mock()
    mock_rag.answer_question.return_value = "A grounded answer."
    monkeypatch.setattr(
        browser_knowledge_routes.rag_manager,
        "get_or_reconstruct_chatbot",
        Mock(return_value=mock_rag),
    )

    uploaded = upload(client, assistant_id, token)
    assert uploaded.status_code == 201, uploaded.text
    assert uploaded.json()["filename"] == "sample.pdf"

    answered = question(client, assistant_id, token)
    assert answered.status_code == 200, answered.text
    assert answered.json()["answer"] == "A grounded answer."


def test_tenant_isolation_blocks_upload_and_query(client):
    token_a = sign_in(client, "first@example.com")
    assistant_a = create_assistant(client, token_a)
    logged_out = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": ORIGIN, "X-CSRF-Token": token_a},
    )
    assert logged_out.status_code == 204

    token_b = sign_in(client, "second@example.com")
    assert upload(client, assistant_a, token_b).status_code == 404
    assert question(client, assistant_a, token_b).status_code == 404


def test_developer_api_key_routes_remain_separate(client):
    sign_in(client, "first@example.com")
    assert client.get("/api/v1/chatbots").status_code == 401
