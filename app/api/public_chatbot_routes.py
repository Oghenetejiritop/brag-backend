
"""Read-only public assistant metadata and rate-limited anonymous RAG questions."""

from collections import defaultdict, deque
from threading import Lock
from time import monotonic

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    Response
)
from fastapi.concurrency import run_in_threadpool

from sqlalchemy.orm import Session
from app.api.chatbot_schemas import (
    ChatbotQueryRequest,
    ChatbotQueryResponse
)

from app.db.database import get_database_session
from app.db.models.user import User
from app.repositories.chatbot_repository import ChatbotRepository
from app.dependencies import rag_manager
from app.exceptions.rag_exceptions import RAGProviderUnavailableError

router = APIRouter(prefix="/api/v1/public/assistants", tags=["Public Assistants"])
_lock = Lock()
_attempts = defaultdict(deque)
_WINDOW = 60
_LIMIT = 10

def _published(chatbot_id: str, session: Session):
    assistant = ChatbotRepository(session).get_published(chatbot_id)
    if assistant is None:
        raise HTTPException(404, "Public assistant not found.")
    owner = session.get(User, assistant.user_id)
    if owner is None or not owner.is_active:
        raise HTTPException(404, "Public assistant not found.")
    return assistant, owner

def _limit(request: Request, chatbot_id: str):
    ip = request.client.host if request.client else "unknown"
    key = (ip, chatbot_id)
    now = monotonic()
    with _lock:
        hits = _attempts[key]
        while hits and now - hits[0] >= _WINDOW:
            hits.popleft()
        if len(hits) >= _LIMIT:
            raise HTTPException(429, "Too many questions. Try again in one minute.", headers={"Retry-After": "60"})
        hits.append(now)

@router.get("/{chatbot_id}")
def public_metadata(chatbot_id: str, response: Response, database_session: Session = Depends(get_database_session)):
    assistant, _ = _published(chatbot_id, database_session)
    response.headers["Cache-Control"] = "no-store"
    return {"chatbot_id": assistant.chatbot_id, "name": assistant.name, "description": assistant.description}

@router.post("/{chatbot_id}/query", response_model=ChatbotQueryResponse)
async def public_query(chatbot_id: str, payload: ChatbotQueryRequest, request: Request, response: Response, database_session: Session = Depends(get_database_session)):
    assistant, owner = _published(chatbot_id, database_session)
    _limit(request, chatbot_id)
    response.headers["Cache-Control"] = "no-store"
    try:
        rag = await run_in_threadpool(rag_manager.get_or_reconstruct_chatbot, user_id=str(owner.user_id), chatbot_id=assistant.chatbot_id)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(409, "This assistant has no ready knowledge base.") from exc
    try:
        answer = await run_in_threadpool(rag.answer_question, question=payload.question, assistant_name=assistant.name, assistant_description=assistant.description)
    except RAGProviderUnavailableError as exc:
        raise HTTPException(503, "The AI provider is temporarily unavailable.", headers={"Retry-After": "30"}) from exc
    return ChatbotQueryResponse(chatbot_id=assistant.chatbot_id, answer=answer)
