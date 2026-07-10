from fastapi import (
    Header,
    HTTPException,
)

from app.models.user_context import UserContext


def get_user_context(
    x_user_id: str = Header(..., alias="X-User-ID"),
) -> UserContext:
    """
    Build the active user context for the current request.

    During Phase 4, BRAG temporarily identifies users through
    the X-User-ID request header.

    Future phases will replace this implementation with API-key
    authentication without changing the route handlers.
    """

    # -------------------------------------------------------------
    # Reject empty user identifiers.
    # -------------------------------------------------------------
    user_id = x_user_id.strip()

    if not user_id:
        raise HTTPException(
            status_code=400,
            detail="X-User-ID header cannot be empty.",
        )

    return UserContext(
        user_id=user_id,
    )
