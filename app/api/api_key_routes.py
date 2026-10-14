
"""
Authenticated BRAG API-key management endpoints.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status
    )

from sqlalchemy.orm import Session

from app.api.api_key_schemas import (
    APIKeyCreationResponse,
    APIKeyResponse,
    )

from app.api.dependencies import get_authenticated_user
from app.db.database import get_database_session
from app.db.models.user import User
from app.services.authentication_service import (
    AuthenticationService,
)


router = APIRouter(
    prefix="/api/v1/api-keys",
    tags=["API Keys"],
)


def get_authentication_service(
    database_session: Session = Depends(
        get_database_session
    ),
) -> AuthenticationService:
    """Create a service using the request database session."""
    return AuthenticationService(
        database_session=database_session
    )


@router.get(
    "",
    response_model=list[APIKeyResponse],
)
def list_api_keys(
    user: User = Depends(get_authenticated_user),
    authentication_service: AuthenticationService = Depends(
        get_authentication_service
    ),
) -> list[APIKeyResponse]:
    """Return only the authenticated user's API-key metadata."""

    keys = authentication_service.list_api_keys(
        user=user
    )

    return [
        APIKeyResponse.model_validate(key)
        for key in keys
    ]

@router.post(
    "",
    response_model=APIKeyCreationResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_api_key(
    response: Response,
    user: User = Depends(get_authenticated_user),
    authentication_service: AuthenticationService = Depends(
        get_authentication_service
    ),
) -> APIKeyCreationResponse:
    """
    Create an API key for the authenticated user.

    The complete credential is returned only once.
    Subsequent listing requests expose metadata only.
    """

    # Prevent caching of a response containing a secret.
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"

    # The user comes from the authenticated dependency,
    # not from client-supplied data.
    result = authentication_service.create_api_key(
        user=user
    )

    return APIKeyCreationResponse(
        api_key_id=result.api_key_id,
        key_prefix=result.key_prefix,
        api_key=result.api_key,
    )

@router.post(
    "/{api_key_id}/revoke",
    response_model=APIKeyResponse,
)
def revoke_api_key(
    api_key_id: int,
    user: User = Depends(get_authenticated_user),
    authentication_service: AuthenticationService = Depends(
        get_authentication_service
    ),
) -> APIKeyResponse:
    """
    Revoke an API key belonging to the authenticated user.

    Return 404 for both nonexistent and foreign keys.
    """

    api_key = authentication_service.revoke_api_key(
        user=user,
        api_key_id=api_key_id,
    )

    if api_key is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="API key not found.",
        )

    return APIKeyResponse.model_validate(api_key)
