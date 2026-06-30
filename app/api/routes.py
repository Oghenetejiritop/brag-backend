import os

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile
    )

from app.api.schemas import QueryRequest, QueryResponse
from app.core.config import DEFAULT_VECTOR_STORE_PATH
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

@router.post("/query", response_model=QueryResponse)
def query(request: QueryRequest):

    if not rag_manager.has_service():
        raise HTTPException(
            status_code=400,
            detail="No document uploaded. Please upload a file first."
        )

    answer = rag_manager.get_service().answer_question(
        request.question
    )

    return QueryResponse(answer=answer)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """
    Upload a document and initialize RAG system.
    """

    file_path = os.path.join("uploads", file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    rag_manager.initialize_from_file(file_path)

    return {
        "message": "Document uploaded and RAG system initialized",
        "filename": file.filename
    }
