
"""
FastAPI dependencies used by BRAG API routes.

Authentication is centralized here so route handlers receive
an authenticated UserContext instead of handling credentials
directly.
"""

from fastapi import (
    Depends,
    HTTPException,
    Security,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from sqlalchemy.orm import Session
from sqlalchemy import select

from app.db.database import get_database_session
from app.db.models.user import User
from app.exceptions.auth_exceptions import AuthenticationError
from app.models.user_context import UserContext
from app.services.authentication_service import AuthenticationService


# -----------------------------------------------------------------
# Register HTTP Bearer authentication with FastAPI/OpenAPI.
#
# auto_error=False lets BRAG return one consistent authentication
# response for missing, invalid, revoked, or inactive credentials.
# -----------------------------------------------------------------
bearer_scheme = HTTPBearer(
    auto_error=False,
)


def get_user_context(
    credentials: HTTPAuthorizationCredentials | None = Security(
        bearer_scheme
    ),
    database_session: Session = Depends(
        get_database_session
    ),
) -> UserContext:
    """
    Authenticate the current request and build its UserContext.

    Requests must supply a BRAG API key through:

        Authorization: Bearer <API_KEY>

    Args:
        credentials:
            Bearer credentials extracted from the HTTP request.

        database_session:
            Request-scoped SQLAlchemy session.

    Returns:
        Authenticated UserContext containing the public user ID.

    Raises:
        HTTPException:
            If authentication fails.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials are required.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    authentication_service = AuthenticationService(
        database_session=database_session
    )

    try:
        user = authentication_service.authenticate(
            credentials.credentials
        )

    except AuthenticationError:
        # ---------------------------------------------------------
        # Return one generic response for authentication failures.
        #
        # We deliberately avoid revealing whether a credential
        # exists, was revoked, or belongs to an inactive user.
        # ---------------------------------------------------------
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or inactive API key.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return UserContext(
        user_id=user.user_id
    )

def get_authenticated_user(
    user_context: UserContext = Depends(get_user_context),
    database_session: Session = Depends(get_database_session),
) -> User:
    """
    Resolve the authenticated API-key owner to a database User.

    The public user UUID comes exclusively from the verified
    authentication dependency, never from client input.

    Raises:
        HTTPException:
            401 if the user no longer exists or is inactive.
    """
    statement = select(User).where(
        User.user_id == user_context.user_id
    )

    user = database_session.scalar(statement)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication is no longer valid.",
            headers={
                "WWW-Authenticate": "Bearer",
            },
        )

    return user
