
"""
Authenticated BRAG API-key management endpoints.
"""

from fastapi import (
    APIRouter,
    Depends
    )

from sqlalchemy.orm import Session

from app.api.api_key_schemas import APIKeyResponse
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
