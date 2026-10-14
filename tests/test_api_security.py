
"""
Phase 5.9.3: Automated BRAG API security tests.

Uses an isolated SQLite database. Never touches the development DB.
"""

from collections.abc import Iterator
from pathlib import Path
from tempfile import TemporaryDirectory

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_database_session
from app.db.models.api_key import APIKey
from app.db.models.chatbot import Chatbot
from app.db.models.user import User
from app.main import app
from app.services.authentication_service import AuthenticationService


@pytest.fixture
def security_environment() -> Iterator[dict]:
    """
    Create two users and their credentials in an isolated database.

    The application database dependency is overridden only while
    this fixture is active.
    """
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, connection_record):
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    testing_session = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    Base.metadata.create_all(bind=engine)

    def override_database_session() -> Iterator[Session]:
        with testing_session() as session:
            yield session

    app.dependency_overrides[get_database_session] = (
        override_database_session
    )

    try:
        with testing_session() as session:
            user_a = User()
            user_b = User()

            session.add_all([user_a, user_b])
            session.commit()

            authentication = AuthenticationService(session)

            key_a = authentication.create_api_key(user_a)
            key_b = authentication.create_api_key(user_b)

            chatbot_b = Chatbot(
                user_id=user_b.id,
                name="User B private chatbot",
            )
            session.add(chatbot_b)
            session.commit()
            session.refresh(chatbot_b)

            data = {
                "key_a": key_a.api_key,
                "key_b": key_b.api_key,
                "key_a_id": key_a.api_key_id,
                "key_b_id": key_b.api_key_id,
                "chatbot_b_id": chatbot_b.chatbot_id,
            }

        with TestClient(app) as client:
            data["client"] = client
            yield data

    finally:
        app.dependency_overrides.pop(
            get_database_session, None
        )
        engine.dispose()


def auth_headers(api_key: str) -> dict[str, str]:
    """Create the Bearer authorization header."""
    return {"Authorization": f"Bearer {api_key}"}


def test_missing_credentials(security_environment: dict) -> None:
    client = security_environment["client"]

    response = client.get("/api/v1/api-keys")

    assert response.status_code == 401


def test_invalid_credentials(security_environment: dict) -> None:
    client = security_environment["client"]

    response = client.get(
        "/api/v1/api-keys",
        headers=auth_headers("brag_live_invalid_test_key"),
    )

    assert response.status_code == 401


def test_user_cannot_list_other_users_keys(
    security_environment: dict,
) -> None:
    client = security_environment["client"]

    response = client.get(
        "/api/v1/api-keys",
        headers=auth_headers(security_environment["key_a"]),
    )

    assert response.status_code == 200

    returned_ids = {
        item["id"] for item in response.json()
    }

    assert security_environment["key_a_id"] in returned_ids
    assert security_environment["key_b_id"] not in returned_ids

    # Neither plaintext credentials nor stored hashes
    # should appear in the listing response.
    for item in response.json():
        assert "api_key" not in item
        assert "key_hash" not in item


def test_user_cannot_revoke_other_users_key(
    security_environment: dict,
) -> None:
    client = security_environment["client"]

    response = client.post(
        f"/api/v1/api-keys/{security_environment['key_b_id']}/revoke",
        headers=auth_headers(security_environment["key_a"]),
    )

    assert response.status_code == 404

    # User B's credential must still work.
    response = client.get(
        "/api/v1/api-keys",
        headers=auth_headers(security_environment["key_b"]),
    )

    assert response.status_code == 200


def test_revoked_key_cannot_authenticate(
    security_environment: dict,
) -> None:
    client = security_environment["client"]

    response = client.post(
        f"/api/v1/api-keys/{security_environment['key_a_id']}/revoke",
        headers=auth_headers(security_environment["key_a"]),
    )

    assert response.status_code == 200
    assert response.json()["is_active"] is False

    response = client.get(
        "/api/v1/api-keys",
        headers=auth_headers(security_environment["key_a"]),
    )

    assert response.status_code == 401


def test_user_cannot_access_other_users_chatbot(
    security_environment: dict,
) -> None:
    client = security_environment["client"]

    response = client.get(
        f"/api/v1/chatbots/{security_environment['chatbot_b_id']}",
        headers=auth_headers(security_environment["key_a"]),
    )

    assert response.status_code == 404

    # User B should still be able to access their chatbot.
    response = client.get(
        f"/api/v1/chatbots/{security_environment['chatbot_b_id']}",
        headers=auth_headers(security_environment["key_b"]),
    )

    assert response.status_code == 200
