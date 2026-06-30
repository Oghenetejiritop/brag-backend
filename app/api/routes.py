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
    Upload a document and initialize the RAG system.
    """

    # -------------------------------------------------------------------------
    # Ensure the upload directory exists.
    # -------------------------------------------------------------------------
    os.makedirs("uploads", exist_ok=True)

    file_path = os.path.join("uploads", file.filename)

    with open(file_path, "wb") as buffer:
        buffer.write(await file.read())

    try:
        rag_manager.initialize_from_file(file_path)

    except Exception as error:
        # ---------------------------------------------------------------------
        # Convert internal exceptions into readable API responses.
        # This also makes debugging much easier during development.
        # ---------------------------------------------------------------------
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    return {
        "message": "Document uploaded successfully.",
        "filename": file.filename,
    }

