
"""
Tests for persistent BRAG browser sessions.

All tests use an isolated SQLite database in memory.
"""

from datetime import timedelta

import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models.user import User
from app.db.models.api_key import APIKey  # noqa: F401
from app.db.models.chatbot import Chatbot  # noqa: F401
from app.db.models.browser_session import BrowserSession

from app.services.browser_session_service import (
    BrowserSessionService,
    hash_session_token,
    utc_now,
)


@pytest.fixture
def database_session():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(engine)

    try:
        with Session(engine) as session:
            yield session
    finally:
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def active_user(database_session):
    user = User()
    database_session.add(user)
    database_session.commit()
    database_session.refresh(user)
    return user


def test_create_session(database_session, active_user):
    service = BrowserSessionService(database_session)

    created = service.create(active_user)

    assert created.token
    assert created.expires_at > utc_now()

    stored = database_session.scalar(
        select(BrowserSession)
    )

    assert stored is not None
    assert stored.user_id == active_user.id
    assert stored.token_hash == hash_session_token(created.token)
    assert created.token != stored.token_hash


def test_valid_session_authenticates(database_session, active_user):
    service = BrowserSessionService(database_session)

    created = service.create(active_user)

    authenticated = service.authenticate(created.token)

    assert authenticated is not None
    assert authenticated.id == active_user.id


def test_invalid_token_rejected(database_session):
    service = BrowserSessionService(database_session)

    assert service.authenticate("invalid-token") is None
    assert service.authenticate(None) is None


def test_expired_session_rejected(database_session, active_user):
    service = BrowserSessionService(database_session)

    created = service.create(active_user)

    stored = database_session.scalar(
        select(BrowserSession)
    )

    stored.expires_at = utc_now() - timedelta(minutes=1)
    database_session.commit()

    assert service.authenticate(created.token) is None


def test_revoked_session_rejected(database_session, active_user):
    service = BrowserSessionService(database_session)

    created = service.create(active_user)

    assert service.revoke(created.token) is True
    assert service.authenticate(created.token) is None
    assert service.revoke(created.token) is False


def test_inactive_user_rejected(database_session, active_user):
    service = BrowserSessionService(database_session)

    created = service.create(active_user)

    active_user.is_active = False
    database_session.commit()

    assert service.authenticate(created.token) is None


def test_sessions_are_user_isolated(database_session, active_user):
    second_user = User()
    database_session.add(second_user)
    database_session.commit()

    service = BrowserSessionService(database_session)

    first_session = service.create(active_user)
    second_session = service.create(second_user)

    assert first_session.token != second_session.token

    first_authenticated = service.authenticate(first_session.token)
    second_authenticated = service.authenticate(second_session.token)

    assert first_authenticated.id == active_user.id
    assert second_authenticated.id == second_user.id


def test_unpersisted_user_rejected(database_session):
    service = BrowserSessionService(database_session)

    with pytest.raises(ValueError):
        service.create(User())
