
"""Browser-session assistant endpoints; developer API-key routes remain unchanged."""

import hmac

from fastapi import (
    APIRouter,
    Depends,
    Header,
    HTTPException,
    Request,
    status
)
from sqlalchemy.orm import Session

from app.api.browser_auth_routes import (
    csrf_for_session,
    get_current_browser_session,
    require_trusted_origin,
)
from app.api.chatbot_schemas import ChatbotCreateRequest, ChatbotResponse
from app.db.database import get_database_session
from app.exceptions.chatbot_exceptions import InvalidChatbotNameError
from app.services.chatbot_service import ChatbotService

router = APIRouter(prefix="/api/v1/browser/chatbots", tags=["Browser Chatbots"])


def authenticated_browser_user(
    request: Request,
    database_session: Session = Depends(get_database_session),
):
    """Resolve user exclusively from a verified browser session."""
    user, _ = get_current_browser_session(request, database_session)
    return user


def require_browser_csrf(
    request: Request,
    x_csrf_token: str | None = Header(default=None),
    database_session: Session = Depends(get_database_session),
):
    """Validate browser session, trusted origin, and session-bound CSRF token."""
    require_trusted_origin(request)
    user, session_token = get_current_browser_session(request, database_session)
    expected = csrf_for_session(session_token)
    if not x_csrf_token or not hmac.compare_digest(x_csrf_token, expected):
        raise HTTPException(status_code=403, detail="Invalid CSRF token.")
    return user


@router.get("", response_model=list[ChatbotResponse])
def list_browser_chatbots(
    user=Depends(authenticated_browser_user),
    database_session: Session = Depends(get_database_session),
):
    """List only assistants owned by the signed-in account."""
    service = ChatbotService(database_session=database_session)
    return [ChatbotResponse.model_validate(item) for item in service.get_user_chatbots(user)]


@router.post("", response_model=ChatbotResponse, status_code=status.HTTP_201_CREATED)
def create_browser_chatbot(
    payload: ChatbotCreateRequest,
    user=Depends(require_browser_csrf),
    database_session: Session = Depends(get_database_session),
):
    """Create an assistant for the signed-in account only."""
    service = ChatbotService(database_session=database_session)
    try:
        assistant = service.create_chatbot(
            user=user, name=payload.name, description=payload.description
        )
    except InvalidChatbotNameError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return ChatbotResponse.model_validate(assistant)


@router.post("/{chatbot_id}/publish", response_model=ChatbotResponse)
def publish_browser_chatbot(chatbot_id: str, user=Depends(require_browser_csrf), database_session: Session = Depends(get_database_session)):
    assistant = ChatbotService(database_session).get_chatbot(user=user, public_chatbot_id=chatbot_id)
    from app.repositories.chatbot_repository import ChatbotRepository
    return ChatbotResponse.model_validate(ChatbotRepository(database_session).set_published(assistant, True))

@router.post("/{chatbot_id}/unpublish", response_model=ChatbotResponse)
def unpublish_browser_chatbot(chatbot_id: str, user=Depends(require_browser_csrf), database_session: Session = Depends(get_database_session)):
    assistant = ChatbotService(database_session).get_chatbot(user=user, public_chatbot_id=chatbot_id, require_active=False)
    from app.repositories.chatbot_repository import ChatbotRepository
    return ChatbotResponse.model_validate(ChatbotRepository(database_session).set_published(assistant, False))
