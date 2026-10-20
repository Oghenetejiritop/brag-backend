"""Manage developer API keys using an authenticated browser session.

Developer API bearer authentication remains separate from browser authentication.
"""

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status
)
from sqlalchemy.orm import Session

from app.api.api_key_schemas import APIKeyCreationResponse, APIKeyResponse
from app.api.browser_chatbot_routes import (
    authenticated_browser_user,
    require_browser_csrf
)
from app.db.database import get_database_session
from app.services.authentication_service import AuthenticationService

router = APIRouter(prefix="/api/v1/browser/api-keys", tags=["Browser Developer API Keys"])


@router.get("", response_model=list[APIKeyResponse])
def list_browser_api_keys(
    user=Depends(authenticated_browser_user),
    database_session: Session = Depends(get_database_session),
) -> list[APIKeyResponse]:
    """Return only the signed-in account's non-secret API-key metadata."""
    service = AuthenticationService(database_session=database_session)
    return [APIKeyResponse.model_validate(key) for key in service.list_api_keys(user=user)]


@router.post("", response_model=APIKeyCreationResponse, status_code=status.HTTP_201_CREATED)
def create_browser_api_key(
    response: Response,
    user=Depends(require_browser_csrf),
    database_session: Session = Depends(get_database_session),
) -> APIKeyCreationResponse:
    """Create a developer credential and disclose its plaintext exactly once."""
    response.headers["Cache-Control"] = "no-store"
    response.headers["Pragma"] = "no-cache"
    service = AuthenticationService(database_session=database_session)
    result = service.create_api_key(user=user)
    return APIKeyCreationResponse(
        api_key_id=result.api_key_id,
        key_prefix=result.key_prefix,
        api_key=result.api_key,
    )


@router.post("/{api_key_id}/revoke", response_model=APIKeyResponse)
def revoke_browser_api_key(
    api_key_id: int,
    user=Depends(require_browser_csrf),
    database_session: Session = Depends(get_database_session),
) -> APIKeyResponse:
    """Revoke only a key owned by this account; hide foreign key existence."""
    service = AuthenticationService(database_session=database_session)
    key = service.revoke_api_key(user=user, api_key_id=api_key_id)
    if key is None:
        raise HTTPException(status_code=404, detail="API key not found.")
    return APIKeyResponse.model_validate(key)
