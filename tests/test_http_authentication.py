
"""
HTTP authentication security tests for BRAG.

These tests exercise the actual FastAPI authentication boundary
while using an isolated in-memory SQLite database.

The production brag.db database is never modified.
"""

from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_database_session
from app.db.database import Base
from app.db.models.api_key import APIKey
from app.db.models.user import User
from app.main import app
from app.repositories.api_key_repository import APIKeyRepository
from app.repositories.user_repository import UserRepository
from app.services.authentication_service import AuthenticationService


# -----------------------------------------------------------------
# StaticPool keeps the same in-memory SQLite database available
# across the different connections used during TestClient requests.
# -----------------------------------------------------------------
TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


def override_database_session(
) -> Generator[Session, None, None]:
    """
    Provide a database session backed by the isolated test database.
    """

    database_session = TestSessionLocal()

    try:
        yield database_session
    finally:
        database_session.close()


def test_http_authentication_security() -> None:
    """
    Validate BRAG authentication behavior through real HTTP requests.

    The test covers:
        - Missing credentials.
        - Invalid credentials.
        - Valid credentials.
        - Revoked API keys.
        - Inactive users.
    """

    # -------------------------------------------------------------
    # Build only the tables required by the authentication system
    # inside the isolated in-memory database.
    # -------------------------------------------------------------
    Base.metadata.create_all(
        bind=test_engine
    )

    app.dependency_overrides[
        get_database_session
    ] = override_database_session

    database_session = TestSessionLocal()

    try:
        user_repository = UserRepository(
            database_session=database_session
        )

        api_key_repository = APIKeyRepository(
            database_session=database_session
        )

        authentication_service = AuthenticationService(
            database_session=database_session
        )

        client = TestClient(app)

        # =========================================================
        # 1. Missing Authorization header
        # =========================================================

        response = client.post(
            "/query",
            json={
                "question": "What is BRAG?"
            },
        )

        assert response.status_code == 401

        assert response.json() == {
            "detail": (
                "Authentication credentials are required."
            )
        }

        assert (
            response.headers.get("www-authenticate")
            == "Bearer"
        )

        print(
            "PASS: Missing credentials return 401."
        )

        # =========================================================
        # 2. Invalid Bearer API key
        # =========================================================

        response = client.post(
            "/query",
            headers={
                "Authorization": (
                    "Bearer brag_live_invalid_key"
                )
            },
            json={
                "question": "What is BRAG?"
            },
        )

        assert response.status_code == 401

        assert response.json() == {
            "detail": "Invalid or inactive API key."
        }

        print(
            "PASS: Invalid API key returns 401."
        )

        # =========================================================
        # 3. Valid active API key
        # =========================================================

        active_user = (
            user_repository.create_user()
        )

        active_key = (
            authentication_service.create_api_key(
                user=active_user
            )
        )

        response = client.post(
            "/query",
            headers={
                "Authorization": (
                    f"Bearer {active_key.api_key}"
                )
            },
            json={
                "question": "What is BRAG?"
            },
        )

        # ---------------------------------------------------------
        # Authentication should succeed.
        #
        # Because this test does not initialize a RAG service,
        # the route should then produce its normal 400 response.
        # A 401 here would indicate authentication failed.
        # ---------------------------------------------------------
        assert response.status_code == 400

        assert response.json() == {
            "detail": (
                "No document uploaded. "
                "Please upload a file first."
            )
        }

        print(
            "PASS: Valid API key reaches "
            "the protected route."
        )

        # =========================================================
        # 4. Revoked API key
        # =========================================================

        active_api_key_record = (
            api_key_repository.get_by_id(
                active_key.api_key_id
            )
        )

        assert active_api_key_record is not None

        api_key_repository.revoke(
            active_api_key_record
        )

        response = client.post(
            "/query",
            headers={
                "Authorization": (
                    f"Bearer {active_key.api_key}"
                )
            },
            json={
                "question": "What is BRAG?"
            },
        )

        assert response.status_code == 401

        assert response.json() == {
            "detail": "Invalid or inactive API key."
        }

        print(
            "PASS: Revoked API key returns 401."
        )

        # =========================================================
        # 5. Valid API key belonging to inactive user
        # =========================================================

        inactive_user = (
            user_repository.create_user()
        )

        inactive_user_key = (
            authentication_service.create_api_key(
                user=inactive_user
            )
        )

        # ---------------------------------------------------------
        # Disable the user only after creating the credential.
        # Authentication must reject an otherwise valid key when
        # its owning account is inactive.
        # ---------------------------------------------------------
        inactive_user.is_active = False

        database_session.commit()

        response = client.post(
            "/query",
            headers={
                "Authorization": (
                    f"Bearer {inactive_user_key.api_key}"
                )
            },
            json={
                "question": "What is BRAG?"
            },
        )

        assert response.status_code == 401

        assert response.json() == {
            "detail": "Invalid or inactive API key."
        }

        print(
            "PASS: API key owned by an "
            "inactive user returns 401."
        )

        print(
            "PASS: HTTP authentication "
            "security validated."
        )

    finally:
        database_session.close()

        # ---------------------------------------------------------
        # Remove the FastAPI override so this test cannot affect
        # other tests executed later in the same Python process.
        # ---------------------------------------------------------
        app.dependency_overrides.clear()

        Base.metadata.drop_all(
            bind=test_engine
        )

        test_engine.dispose()


if __name__ == "__main__":
    test_http_authentication_security()
