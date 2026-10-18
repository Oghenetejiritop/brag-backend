
"""
Tests for BRAG email/password account registration.

These tests use an isolated in-memory SQLite database.
They never write to the development brag.db file.
"""

import pytest

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db.database import Base
from app.db.models.user import User

# Import related models so SQLAlchemy can resolve relationships.
from app.db.models.api_key import APIKey  # noqa: F401
from app.db.models.chatbot import Chatbot  # noqa: F401

from app.services.account_registration_service import (
    AccountRegistrationService,
    DuplicateEmailError,
    RegistrationError,
)


@pytest.fixture
def database_session():
    """Provide a new isolated database for each test."""
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


def test_register_creates_account(database_session):
    service = AccountRegistrationService(database_session)

    user = service.register(
        "  Student@Example.com  ",
        "CorrectHorseBatteryStaple2026!",
    )

    assert user.id is not None
    assert user.user_id is not None
    assert user.email == "student@example.com"
    assert user.is_active is True


def test_password_is_hashed(database_session):
    service = AccountRegistrationService(database_session)

    password = "A-Long-Unique-Test-Password-2026"

    user = service.register(
        "secure@example.com",
        password,
    )

    assert user.password_hash is not None
    assert user.password_hash != password
    assert user.password_hash.startswith("$argon2id$")


def test_correct_password_authenticates(database_session):
    service = AccountRegistrationService(database_session)

    registered = service.register(
        "person@example.com",
        "Correct-Password-2026!",
    )

    authenticated = service.verify_credentials(
        "PERSON@example.com",
        "Correct-Password-2026!",
    )

    assert authenticated is not None
    assert authenticated.id == registered.id


def test_wrong_password_is_rejected(database_session):
    service = AccountRegistrationService(database_session)

    service.register(
        "person@example.com",
        "Correct-Password-2026!",
    )

    assert service.verify_credentials(
        "person@example.com",
        "Incorrect-Password-2026!",
    ) is None


def test_duplicate_email_is_rejected(database_session):
    service = AccountRegistrationService(database_session)

    service.register(
        "person@example.com",
        "Correct-Password-2026!",
    )

    with pytest.raises(DuplicateEmailError):
        service.register(
            " PERSON@EXAMPLE.COM ",
            "Another-Password-2026!",
        )

    users = database_session.scalars(
        select(User)
    ).all()

    assert len(users) == 1


def test_short_password_is_rejected(database_session):
    service = AccountRegistrationService(database_session)

    with pytest.raises(RegistrationError):
        service.register(
            "person@example.com",
            "short",
        )


def test_invalid_email_is_rejected(database_session):
    service = AccountRegistrationService(database_session)

    with pytest.raises(RegistrationError):
        service.register(
            "not-an-email",
            "Correct-Password-2026!",
        )


def test_inactive_account_cannot_authenticate(database_session):
    service = AccountRegistrationService(database_session)

    user = service.register(
        "person@example.com",
        "Correct-Password-2026!",
    )

    user.is_active = False
    database_session.commit()

    assert service.verify_credentials(
        "person@example.com",
        "Correct-Password-2026!",
    ) is None


def test_existing_api_key_only_user_is_preserved(database_session):
    service = AccountRegistrationService(database_session)

    legacy_user = User()
    database_session.add(legacy_user)
    database_session.commit()

    registered = service.register(
        "new@example.com",
        "Correct-Password-2026!",
    )

    database_session.refresh(legacy_user)

    assert legacy_user.email is None
    assert legacy_user.password_hash is None
    assert legacy_user.id != registered.id

    assert service.verify_credentials(
        "new@example.com",
        "Correct-Password-2026!",
    ) is not None
