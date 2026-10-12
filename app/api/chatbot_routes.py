
"""
Versioned REST API endpoints for persistent BRAG chatbots.

All chatbot operations require an authenticated database user.
Business rules and ownership checks are delegated to ChatbotService.
"""

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.api.chatbot_schemas import (
    ChatbotCreateRequest,
    ChatbotResponse,
)
from app.api.dependencies import get_authenticated_user
from app.db.database import get_database_session
from app.db.models.user import User
from app.services.chatbot_service import ChatbotService


router = APIRouter(
    prefix="/api/v1/chatbots",
    tags=["Chatbots"],
)


def get_chatbot_service(
    database_session: Session = Depends(get_database_session),
) -> ChatbotService:
    """Create a chatbot service using the request database session."""
    return ChatbotService(
        database_session=database_session,
    )


@router.post(
    "",
    response_model=ChatbotResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_chatbot(
    request: ChatbotCreateRequest,
    user: User = Depends(get_authenticated_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
) -> ChatbotResponse:
    """Create a chatbot owned by the authenticated user."""
    chatbot = chatbot_service.create_chatbot(
        user=user,
        name=request.name,
        description=request.description,
    )

    return ChatbotResponse.model_validate(chatbot)


@router.get(
    "",
    response_model=list[ChatbotResponse],
)
def list_chatbots(
    user: User = Depends(get_authenticated_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
) -> list[ChatbotResponse]:
    """List chatbots belonging to the authenticated user."""
    chatbots = chatbot_service.get_user_chatbots(
        user=user,
    )

    return [
        ChatbotResponse.model_validate(chatbot)
        for chatbot in chatbots
    ]


@router.get(
    "/{chatbot_id}",
    response_model=ChatbotResponse,
)
def get_chatbot(
    chatbot_id: str,
    user: User = Depends(get_authenticated_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
) -> ChatbotResponse:
    """Retrieve a chatbot after enforcing ownership."""
    chatbot = chatbot_service.get_chatbot(
        user=user,
        public_chatbot_id=chatbot_id,
    )

    return ChatbotResponse.model_validate(chatbot)


@router.patch(
    "/{chatbot_id}/deactivate",
    response_model=ChatbotResponse,
)
def deactivate_chatbot(
    chatbot_id: str,
    user: User = Depends(get_authenticated_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
) -> ChatbotResponse:
    """Deactivate an owned chatbot."""
    chatbot = chatbot_service.deactivate_chatbot(
        user=user,
        public_chatbot_id=chatbot_id,
    )

    return ChatbotResponse.model_validate(chatbot)
