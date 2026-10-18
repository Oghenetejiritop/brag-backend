
"""
Integration tests for BRAG browser authentication.

No tests in this module write to the development database.
"""

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_database_session
from app.db.models.api_key import APIKey  # noqa: F401
from app.db.models.browser_session import BrowserSession  # noqa: F401
from app.db.models.chatbot import Chatbot  # noqa: F401
from app.db.models.user import User  # noqa: F401
from app.main import app

from app.api.browser_auth_routes import (
    _rate_limit_attempts,
    _rate_limit_lock,
)


ORIGIN = "http://testserver"
PASSWORD = "Correct-Password-2026!"


@pytest.fixture
def client():
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

    with _rate_limit_lock:
        _rate_limit_attempts.clear()

    try:
        with TestClient(
            app,
            base_url=ORIGIN,
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        with _rate_limit_lock:
            _rate_limit_attempts.clear()
        engine.dispose()


def register_account(
    client,
    email="student@example.com",
    password=PASSWORD,
):
    return client.post(
        "/api/v1/auth/register",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": password},
    )


def login_account(
    client,
    email="student@example.com",
    password=PASSWORD,
):
    return client.post(
        "/api/v1/auth/login",
        headers={"Origin": ORIGIN},
        json={"email": email, "password": password},
    )


def test_register_account(client):
    response = register_account(client)

    assert response.status_code == 201
    assert response.json()["email"] == "student@example.com"
    assert response.json()["user_id"]
    assert "password" not in response.json()
    assert "password_hash" not in response.json()


def test_duplicate_email_rejected(client):
    assert register_account(client).status_code == 201

    response = register_account(
        client,
        email="STUDENT@example.com",
    )

    assert response.status_code == 409


def test_login_sets_http_only_cookie(client):
    register_account(client)

    response = login_account(client)

    assert response.status_code == 200
    assert response.json()["csrf_token"]

    cookie = response.headers["set-cookie"].lower()

    assert "httponly" in cookie
    assert "samesite=strict" in cookie
    assert "brag_session=" in cookie


def test_me_returns_authenticated_account(client):
    register_account(client)
    assert login_account(client).status_code == 200

    response = client.get("/api/v1/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == "student@example.com"


def test_me_requires_authentication(client):
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401


def test_wrong_password_rejected(client):
    register_account(client)

    response = login_account(
        client,
        password="Incorrect-Password-2026!",
    )

    assert response.status_code == 401


def test_logout_revokes_session(client):
    register_account(client)
    login_response = login_account(client)

    csrf_token = login_response.json()["csrf_token"]

    response = client.post(
        "/api/v1/auth/logout",
        headers={
            "Origin": ORIGIN,
            "X-CSRF-Token": csrf_token,
        },
    )

    assert response.status_code == 204
    assert client.get("/api/v1/auth/me").status_code == 401


def test_logout_requires_csrf_token(client):
    register_account(client)
    login_account(client)

    response = client.post(
        "/api/v1/auth/logout",
        headers={"Origin": ORIGIN},
    )

    assert response.status_code == 403
    assert client.get("/api/v1/auth/me").status_code == 200


def test_logout_rejects_wrong_csrf_token(client):
    register_account(client)
    login_account(client)

    response = client.post(
        "/api/v1/auth/logout",
        headers={
            "Origin": ORIGIN,
            "X-CSRF-Token": "incorrect",
        },
    )

    assert response.status_code == 403


def test_cross_origin_login_rejected(client):
    response = client.post(
        "/api/v1/auth/login",
        headers={"Origin": "https://untrusted.example"},
        json={
            "email": "student@example.com",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 403


def test_missing_origin_registration_rejected(client):
    response = client.post(
        "/api/v1/auth/register",
        headers={"Origin": ""},
        json={
            "email": "student@example.com",
            "password": PASSWORD,
        },
    )

    assert response.status_code == 403


def test_login_rate_limit(client):
    for _ in range(10):
        response = login_account(client)
        assert response.status_code == 401

    blocked = login_account(client)

    assert blocked.status_code == 429


def test_registration_rate_limit(client):
    for index in range(5):
        response = register_account(
            client,
            email=f"student{index}@example.com",
        )
        assert response.status_code == 201

    blocked = register_account(
        client,
        email="student5@example.com",
    )

    assert blocked.status_code == 429


def test_api_key_routes_remain_protected(client):
    response = client.get("/api/v1/chatbots")

    assert response.status_code == 401


def test_browser_login_does_not_bypass_api_key_auth(client):
    register_account(client)
    assert login_account(client).status_code == 200

    response = client.get("/api/v1/chatbots")

    assert response.status_code == 401
