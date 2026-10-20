
"""
Browser-session PDF knowledge upload and document-grounded questions.

Developer API-key endpoints remain unchanged. Every operation resolves
assistant ownership before accessing a knowledge source or RAG service.
"""

from pathlib import Path

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status
)
from fastapi.concurrency import run_in_threadpool
from sqlalchemy.orm import Session

from app.api.browser_chatbot_routes import (
    authenticated_browser_user,
    require_browser_csrf,
)
from app.api.chatbot_schemas import ChatbotQueryRequest, ChatbotQueryResponse
from app.db.database import get_database_session
from app.dependencies import rag_manager, upload_service
from app.exceptions.rag_exceptions import RAGProviderUnavailableError
from app.exceptions.upload_exceptions import (
    EmptyFilenameError,
    FileTooLargeError,
    UnsupportedDocumentTypeError,
)
from app.services.chatbot_service import ChatbotService

router = APIRouter(
    prefix="/api/v1/browser/chatbots",
    tags=["Browser Knowledge and Conversations"],
)


def owned_assistant(user, chatbot_id: str, database_session: Session):
    """Require an active assistant belonging to the signed-in user."""
    service = ChatbotService(database_session=database_session)
    return service.get_chatbot(user=user, public_chatbot_id=chatbot_id)


@router.post(
    "/{chatbot_id}/documents",
    status_code=status.HTTP_201_CREATED,
)
async def upload_browser_document(
    chatbot_id: str,
    file: UploadFile = File(...),
    user=Depends(require_browser_csrf),
    database_session: Session = Depends(get_database_session),
) -> dict[str, str]:
    """Upload one PDF into the authenticated user's assistant workspace."""
    assistant = owned_assistant(user, chatbot_id, database_session)

    filename = (file.filename or "").replace("\\", "/").split("/")[-1]
    if not filename or Path(filename).suffix.lower() != ".pdf":
        raise HTTPException(status_code=415, detail="Select a PDF document.")

    # A filename alone is insufficient; reject obvious non-PDF content.
    signature = await file.read(5)
    await file.seek(0)
    if signature != b"%PDF-":
        raise HTTPException(status_code=415, detail="The file is not a valid PDF header.")

    user_id = str(user.user_id)
    assistant_id = str(assistant.chatbot_id)

    try:
        file_path = await upload_service.save_chatbot_file(
            user_id=user_id,
            chatbot_id=assistant_id,
            file=file,
        )
    except (EmptyFilenameError, UnsupportedDocumentTypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileTooLargeError as exc:
        raise HTTPException(status_code=413, detail="The PDF exceeds the 10 MiB limit.") from exc

    try:
        await run_in_threadpool(
            rag_manager.initialize_chatbot_from_file,
            file_path=file_path,
            user_id=user_id,
            chatbot_id=assistant_id,
        )
    except (ValueError, FileNotFoundError) as exc:
        Path(file_path).unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="The PDF could not be processed.") from exc

    return {
        "message": "PDF uploaded and processed successfully.",
        "chatbot_id": assistant_id,
        "filename": filename,
    }


@router.post(
    "/{chatbot_id}/query",
    response_model=ChatbotQueryResponse,
)
async def query_browser_assistant(
    chatbot_id: str,
    payload: ChatbotQueryRequest,
    user=Depends(require_browser_csrf),
    database_session: Session = Depends(get_database_session),
) -> ChatbotQueryResponse:
    """Answer a question from the signed-in user's assistant knowledge."""
    assistant = owned_assistant(user, chatbot_id, database_session)
    user_id = str(user.user_id)
    assistant_id = str(assistant.chatbot_id)

    try:
        rag_service = await run_in_threadpool(
            rag_manager.get_or_reconstruct_chatbot,
            user_id=user_id,
            chatbot_id=assistant_id,
        )
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(
            status_code=409,
            detail="This assistant has no ready knowledge base. Upload a PDF first.",
        ) from exc

    try:
        answer = await run_in_threadpool(
            rag_service.answer_question,
            question=payload.question,
        )
    except RAGProviderUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail="The AI provider is temporarily unavailable.",
            headers={"Retry-After": "30"},
        ) from exc

    return ChatbotQueryResponse(chatbot_id=assistant_id, answer=answer)
