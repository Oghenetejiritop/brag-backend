
"""
Versioned REST API endpoints for persistent BRAG chatbots.

All chatbot operations require an authenticated database user.
Business rules and ownership checks are delegated to ChatbotService.
"""

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    status,
    UploadFile,
    )

from fastapi.concurrency import run_in_threadpool

from sqlalchemy.orm import Session

from app.api.chatbot_schemas import (
    ChatbotCreateRequest,
    ChatbotQueryRequest,
    ChatbotQueryResponse,
    ChatbotResponse,
)

from app.api.dependencies import get_authenticated_user
from app.db.database import get_database_session
from app.db.models.user import User
from app.services.chatbot_service import ChatbotService

from app.dependencies import (
    rag_manager,
    upload_service
    )

from app.exceptions.chatbot_exceptions import InvalidChatbotNameError
from app.exceptions.rag_exceptions import RAGProviderUnavailableError
from app.exceptions.upload_exceptions import (
    EmptyFilenameError,
    FileTooLargeError,
    UnsupportedDocumentTypeError,
)

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
    try:
        chatbot = chatbot_service.create_chatbot(
            user=user,
            name=request.name,
            description=request.description,
        )
    except InvalidChatbotNameError:
        raise
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
    ) from error

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


@router.post(
    "/{chatbot_id}/documents",
    status_code=status.HTTP_201_CREATED,
)
async def upload_chatbot_document(
    chatbot_id: str,
    file: UploadFile = File(...),
    user: User = Depends(get_authenticated_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
) -> dict[str, str]:
    """
    Upload and ingest a document for an owned, active chatbot.

    Ownership is checked before any file is saved.
    """

    # Step 1: Verify chatbot ownership and active status.
    chatbot = chatbot_service.get_chatbot(
        user=user,
        public_chatbot_id=chatbot_id,
    )

    # Use the authenticated user's public UUID and the
    # canonical chatbot UUID returned from the database.
    user_id = str(user.user_id)
    authorized_chatbot_id = str(chatbot.chatbot_id)

    # Step 2: Save the document to the chatbot workspace.
    try:
        file_path = await upload_service.save_chatbot_file(
            user_id=user_id,
            chatbot_id=authorized_chatbot_id,
            file=file,
        )

    except (EmptyFilenameError, UnsupportedDocumentTypeError) as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    except FileTooLargeError as error:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=str(error),
        ) from error

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid document upload.",
        ) from error

    # Step 3: Ingest into the chatbot's persistent vector store.
    try:
        rag_manager.initialize_chatbot_from_file(
            file_path=file_path,
            user_id=user_id,
            chatbot_id=authorized_chatbot_id,
        )

    except (ValueError, FileNotFoundError) as error:
        # A saved file is not proof of successful ingestion.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="The document could not be ingested.",
        ) from error

    # Step 4: Return a successful response.
    return {
        "message": "Document uploaded and ingested successfully.",
        "chatbot_id": authorized_chatbot_id,
        "filename": Path(file.filename).name,
    }


@router.post(
    "/{chatbot_id}/query",
    response_model=ChatbotQueryResponse,
)
async def query_chatbot(
    chatbot_id: str,
    request: ChatbotQueryRequest,
    user: User = Depends(get_authenticated_user),
    chatbot_service: ChatbotService = Depends(get_chatbot_service),
) -> ChatbotQueryResponse:
    """
    Answer a question using an owned, active chatbot.

    The chatbot must have an existing knowledge base.
    """

    # 1. Verify ownership and active status first.
    chatbot = chatbot_service.get_chatbot(
        user=user,
        public_chatbot_id=chatbot_id,
    )

    user_id = str(user.user_id)
    authorized_chatbot_id = str(chatbot.chatbot_id)

    # 2. Load the chatbot's RAG pipeline.
    try:
        rag_service = await run_in_threadpool(
            rag_manager.get_or_reconstruct_chatbot,
            user_id=user_id,
            chatbot_id=authorized_chatbot_id,
        )

    except (FileNotFoundError, ValueError) as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=(
                "This chatbot has no initialized knowledge base. "
                "Upload a document first."
            ),
        ) from error

    # 3. Generate an answer.
    # This is run in a worker thread because the existing
    # answer_question method is synchronous.
    try:
        answer = await run_in_threadpool(
            rag_service.answer_question,
            question=request.question,
            assistant_name=chatbot.name,
            assistant_description=chatbot.description,
        )
    except RAGProviderUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The AI service is temporarily unavailable.",
            headers={"Retry-After": "30"},
        ) from error

    # 4. Return the answer.
    return ChatbotQueryResponse(
        chatbot_id=authorized_chatbot_id,
        answer=answer,
    )
