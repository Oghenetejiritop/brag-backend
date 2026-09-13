
"""
Authentication persistence tests for BRAG.

These tests verify that users, API-key hashes, and revocation
state survive completely separate SQLAlchemy sessions.

A temporary file-backed SQLite database is used so the
production brag.db database is never modified.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, event
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)

from app.db.database import Base
from app.db.models.api_key import APIKey
from app.db.models.user import User
from app.exceptions.auth_exceptions import InactiveAPIKeyError
from app.repositories.api_key_repository import APIKeyRepository
from app.repositories.user_repository import UserRepository
from app.services.authentication_service import AuthenticationService


def test_authentication_persistence() -> None:
    """
    Verify authentication state across independent DB sessions.

    The test confirms that:
        - A persisted user survives the original session.
        - An API-key hash survives the original session.
        - The same plaintext key authenticates through a new session.
        - The same public user UUID is recovered.
        - API-key revocation persists across later sessions.
    """

    with TemporaryDirectory() as temporary_directory:
        database_path = (
            Path(temporary_directory)
            / "brag_test.db"
        )

        database_url = (
            f"sqlite:///{database_path.as_posix()}"
        )

        test_engine = create_engine(
            database_url,
            connect_args={
                "check_same_thread": False,
            },
        )

        # ---------------------------------------------------------
        # Match BRAG's production SQLite behavior by enabling
        # foreign-key enforcement for every test connection.
        # ---------------------------------------------------------
        @event.listens_for(
            test_engine,
            "connect",
        )
        def enable_foreign_keys(
            database_connection,
            connection_record,
        ) -> None:
            """
            Enable SQLite foreign-key constraints in the test DB.
            """

            del connection_record

            cursor = database_connection.cursor()

            try:
                cursor.execute(
                    "PRAGMA foreign_keys=ON"
                )
            finally:
                cursor.close()

        TestSessionLocal = sessionmaker(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        )

        Base.metadata.create_all(
            bind=test_engine
        )

        plaintext_api_key: str
        expected_user_id: str
        api_key_id: int

        # =========================================================
        # SESSION 1
        #
        # Create and persist the user and API key.
        # =========================================================

        session_one: Session = TestSessionLocal()

        try:
            user_repository = UserRepository(
                database_session=session_one
            )

            authentication_service = AuthenticationService(
                database_session=session_one
            )

            user = user_repository.create_user()

            api_key_result = (
                authentication_service.create_api_key(
                    user=user
                )
            )

            expected_user_id = user.user_id
            plaintext_api_key = api_key_result.api_key
            api_key_id = api_key_result.api_key_id

            assert expected_user_id
            assert plaintext_api_key
            assert api_key_id

        finally:
            session_one.close()

        print(
            "PASS: User and API key persisted "
            "before original session closed."
        )

        # =========================================================
        # SESSION 2
        #
        # Authenticate using an entirely new Session.
        # =========================================================

        session_two: Session = TestSessionLocal()

        try:
            authentication_service = AuthenticationService(
                database_session=session_two
            )

            authenticated_user = (
                authentication_service.authenticate(
                    plaintext_api_key
                )
            )

            assert (
                authenticated_user.user_id
                == expected_user_id
            )

        finally:
            session_two.close()

        print(
            "PASS: API key authenticated "
            "through a new database session."
        )

        print(
            "PASS: Persistent user identity "
            "survived session replacement."
        )

        # =========================================================
        # SESSION 3
        #
        # Revoke the API key through another independent Session.
        # =========================================================

        session_three: Session = TestSessionLocal()

        try:
            api_key_repository = APIKeyRepository(
                database_session=session_three
            )

            persisted_api_key = (
                api_key_repository.get_by_id(
                    api_key_id
                )
            )

            assert persisted_api_key is not None

            api_key_repository.revoke(
                persisted_api_key
            )

            assert (
                persisted_api_key.is_active
                is False
            )

        finally:
            session_three.close()

        print(
            "PASS: API-key revocation persisted "
            "through a separate session."
        )

        # =========================================================
        # SESSION 4
        #
        # Verify the revoked state through yet another Session.
        # =========================================================

        session_four: Session = TestSessionLocal()

        try:
            authentication_service = AuthenticationService(
                database_session=session_four
            )

            try:
                authentication_service.authenticate(
                    plaintext_api_key
                )

            except InactiveAPIKeyError:
                pass

            else:
                raise AssertionError(
                    "Revoked API key authenticated "
                    "after session replacement."
                )

        finally:
            session_four.close()

        print(
            "PASS: Revoked API key remained "
            "invalid in a new database session."
        )

        # ---------------------------------------------------------
        # Security check:
        #
        # Verify that the database contains the hash/prefix record,
        # not the plaintext API credential.
        # ---------------------------------------------------------
        session_five: Session = TestSessionLocal()

        try:
            persisted_api_key = session_five.get(
                APIKey,
                api_key_id,
            )

            assert persisted_api_key is not None

            assert (
                persisted_api_key.key_hash
                != plaintext_api_key
            )

            assert (
                persisted_api_key.key_prefix
                != plaintext_api_key
            )

        finally:
            session_five.close()

        print(
            "PASS: Plaintext API key is not "
            "stored in the API-key record."
        )

        Base.metadata.drop_all(
            bind=test_engine
        )

        test_engine.dispose()

        print(
            "PASS: Authentication persistence "
            "validated."
        )


if __name__ == "__main__":
    test_authentication_persistence()
