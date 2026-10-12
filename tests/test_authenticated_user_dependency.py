
"""
Tests for resolving authenticated users to SQLAlchemy models.

No real database or API key is required for these unit tests.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

from fastapi import HTTPException

from app.api.dependencies import get_authenticated_user
from app.models.user_context import UserContext


def test_authenticated_user_dependency() -> None:
    """Verify successful lookup and rejection of invalid users."""
    public_user_id = str(uuid4())

    context = UserContext(user_id=public_user_id)

    session = MagicMock()

    # Case 1: Active authenticated user.
    active_user = SimpleNamespace(
        id=42,
        user_id=public_user_id,
        is_active=True,
    )

    session.scalar.return_value = active_user

    result = get_authenticated_user(
        user_context=context,
        database_session=session,
    )

    assert result is active_user
    assert result.user_id == public_user_id
    assert session.scalar.call_count == 1

    print("PASS: Authenticated user resolved.")

    # Case 2: User record no longer exists.
    session.scalar.return_value = None

    try:
        get_authenticated_user(
            user_context=context,
            database_session=session,
        )
    except HTTPException as error:
        assert error.status_code == 401
    else:
        raise AssertionError(
            "Missing authenticated user was accepted."
        )

    print("PASS: Missing user rejected.")

    # Case 3: User has been deactivated.
    inactive_user = SimpleNamespace(
        id=42,
        user_id=public_user_id,
        is_active=False,
    )

    session.scalar.return_value = inactive_user

    try:
        get_authenticated_user(
            user_context=context,
            database_session=session,
        )
    except HTTPException as error:
        assert error.status_code == 401
    else:
        raise AssertionError(
            "Inactive authenticated user was accepted."
        )

    print("PASS: Inactive user rejected.")
    print("PASS: Authenticated user dependency validated.")


if __name__ == "__main__":
    test_authenticated_user_dependency()
