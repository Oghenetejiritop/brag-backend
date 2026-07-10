
from fastapi import (
    APIRouter,
    File,
    Header,
    HTTPException,
    UploadFile
    )

from app.api.schemas import (
    QueryRequest,
    QueryResponse
    )

from app.dependencies import (
    model_service,
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


@router.get("/models")
def get_models():
    """
    Retrieve the language models currently supported by BRAG.

    Returns:
        Information about the default language model and the
        complete list of available models.
    """

    return model_service.get_models()


@router.post("/query", response_model=QueryResponse)
def query(
    request: QueryRequest,
    user_id: str = Header(
        ...,
        alias="X-User-ID",
    ),
    ):

    # Reserved for Phase 4.3.
    # The active RAG service will be selected using the user ID.
    # -----------------------------------------------------------------

    if not rag_manager.has_service(user_id):
        raise HTTPException(
            status_code=400,
            detail="No document uploaded. Please upload a file first."
        )

    answer = rag_manager.get_service(
        user_id=user_id,
    ).answer_question(
        request.question
    )

    return QueryResponse(answer=answer)


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_id: str = Header(
        ...,
        alias="X-User-ID",
    ),
    ):
    """
    Upload a document for the specified user and initialize
    that user's active RAG pipeline.

        During Phase 4, the user is identified through the
        temporary X-User-ID request header.

            Future phases will replace this mechanism with API-key
        authentication.
    """

    try:
        # Save the uploaded document.
        file_path = await upload_service.save_file(
    user_id=user_id,
            file=file,
            )

        # Initialize the RAG pipeline using the saved document.
        rag_manager.initialize_from_file(
            user_id=user_id,
            file_path=file_path
            )

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

