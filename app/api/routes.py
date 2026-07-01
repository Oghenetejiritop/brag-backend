

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile
    )

from app.api.schemas import (
    QueryRequest,
    QueryResponse
    )

from app.dependencies import (
    rag_manager,
    upload_service
    )

from app.exceptions.upload_exceptions import (
    EmptyFilenameError,
    UnsupportedDocumentTypeError,
)


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
    Upload a document and initialize the active RAG system.
    """

    try:
        # Save the uploaded document.
        file_path = await upload_service.save_file(file)

        # Initialize the RAG pipeline using the saved document.
        rag_manager.initialize_from_file(file_path)

    except UnsupportedDocumentTypeError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except EmptyFilenameError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error),
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=str(error),
        )

    return {
        "message": "Document uploaded successfully.",
        "filename": file.filename,
    }

