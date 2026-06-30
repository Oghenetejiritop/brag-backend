from fastapi import APIRouter
from fastapi import HTTPException

from app.api.schemas import QueryRequest, QueryResponse
from app.dependencies import rag_manager


router = APIRouter()


@router.get("/")
def root():
    """
    Root endpoint.
    """

    return {
        "message": "Welcome to BRAG API"
    }


@router.get("/health")
def health():
    """
    Health check endpoint.
    """

    return {
        "status": "healthy"
    }

@router.post("/query", response_model=QueryResponse,)
def query(request: QueryRequest):

    if not rag_manager.has_service():
        raise HTTPException(
            status_code=400,
            detail="No knowledge base has been uploaded."
        )

    answer = rag_manager.get_service().answer_question(
        request.question
    )

    return QueryResponse(
        answer=answer
    )

