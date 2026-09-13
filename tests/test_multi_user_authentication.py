
"""
Multi-user authentication isolation tests for BRAG.

These tests verify that API credentials resolve only to the
user that owns them and that separate users receive independent
authentication identities.
"""

from sqlalchemy.orm import Session

from app.db.database import SessionLocal
from app.db.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.authentication_service import AuthenticationService


def test_two_user_authentication_isolation() -> None:
    """
    Verify that separate API keys authenticate separate users.

    The test creates two persistent users, generates an API key
    for each user, and confirms that each credential resolves
    only to its owning account.

    Test users are deleted afterward so the development database
    is not permanently filled with validation records.
    """

    database_session: Session = SessionLocal()

    user_a: User | None = None
    user_b: User | None = None

    try:
        user_repository = UserRepository(
            database_session=database_session
        )

        authentication_service = AuthenticationService(
            database_session=database_session
        )

        # ---------------------------------------------------------
        # Create two independent BRAG users.
        # ---------------------------------------------------------
        user_a = user_repository.create_user()
        user_b = user_repository.create_user()

        assert user_a.id != user_b.id
        assert user_a.user_id != user_b.user_id

        # ---------------------------------------------------------
        # Issue one credential to each user.
        #
        # Plaintext credentials remain only in memory and are
        # intentionally not printed to the terminal.
        # ---------------------------------------------------------
        key_a = authentication_service.create_api_key(
            user=user_a
        )

        key_b = authentication_service.create_api_key(
            user=user_b
        )

        assert key_a.api_key_id != key_b.api_key_id
        assert key_a.api_key != key_b.api_key

        # ---------------------------------------------------------
        # Authenticate each credential independently.
        # ---------------------------------------------------------
        authenticated_user_a = (
            authentication_service.authenticate(
                key_a.api_key
            )
        )

        authenticated_user_b = (
            authentication_service.authenticate(
                key_b.api_key
            )
        )

        # ---------------------------------------------------------
        # The credential must resolve to its actual database owner.
        # ---------------------------------------------------------
        assert authenticated_user_a.id == user_a.id
        assert authenticated_user_a.user_id == user_a.user_id

        assert authenticated_user_b.id == user_b.id
        assert authenticated_user_b.user_id == user_b.user_id

        # ---------------------------------------------------------
        # Confirm the two authenticated identities remain isolated.
        # ---------------------------------------------------------
        assert authenticated_user_a.id != authenticated_user_b.id
        assert (
            authenticated_user_a.user_id
            != authenticated_user_b.user_id
        )

        print(
            "PASS: User A authenticated as:",
            authenticated_user_a.user_id,
        )

        print(
            "PASS: User B authenticated as:",
            authenticated_user_b.user_id,
        )

        print(
            "PASS: API-key identity isolation validated."
        )

    finally:
        # ---------------------------------------------------------
        # Remove temporary validation users.
        #
        # The User -> APIKey relationship uses delete-orphan
        # cascading, so their test API-key records are removed
        # together with the users.
        # ---------------------------------------------------------
        if user_a is not None:
            database_session.delete(user_a)

        if user_b is not None:
            database_session.delete(user_b)

        try:
            database_session.commit()
        except Exception:
            database_session.rollback()
            raise
        finally:
            database_session.close()


if __name__ == "__main__":
    test_two_user_authentication_isolation()

