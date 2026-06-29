from fastapi import APIRouter

from app.api.schemas import QueryRequest, QueryResponse
from app.dependencies import rag_service


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
def query(request: QueryRequest,):
    """
    Query the BRAG knowledge base.
    """

    answer = rag_service.answer_question(request.question)

    return QueryResponse(
        answer=answer
    )

