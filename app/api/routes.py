
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    )

from app.api.dependencies import get_user_context
from app.api.schemas import (
    QueryRequest,
    QueryResponse,
    )

from app.dependencies import (
    model_service,
    rag_manager,
    upload_service,
    )

from app.exceptions.upload_exceptions import (
    EmptyFilenameError,
    FileTooLargeError,
    UnsupportedDocumentTypeError,
)

from app.models.user_context import UserContext


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


@router.post(
        "/query",
        response_model=QueryResponse
        )
def query(
    request: QueryRequest,
    user_context: UserContext = Depends(get_user_context),
    ):
    """
    Query the authenticated user's RAG knowledge base.
    """

    if not rag_manager.has_service(
        user_context.user_id
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "No document uploaded. "
                "Please upload a file first."
            ),
        )

    answer = rag_manager.get_service(
        user_id=user_context.user_id,
    ).answer_question(
        request.question
    )

    return QueryResponse(
        answer=answer
    )


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    user_context: UserContext = Depends(get_user_context),
    ):
    """
    Upload a document for the authenticated user and
    initialize that user's RAG pipeline.

    The active user is resolved from the BRAG API key supplied
    through the Authorization Bearer header.
    """

    try:
        # Save the uploaded document.
        file_path = await upload_service.save_file(
            file=file,
            user_id=user_context.user_id,
        )

        # Initialize the RAG pipeline using the saved document.
        rag_manager.initialize_from_file(
            file_path=file_path,
            user_id=user_context.user_id,
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

    except FileTooLargeError as error:
        raise HTTPException(
            status_code=413,
            detail="Uploaded file exceeds the 10 MiB limit.",
        ) from error

    # Unexpected exceptions are handled by the centralized 500 handler.
    # Never return str(error) to clients: it may contain secrets or paths.

    return {
        "message": "Document uploaded successfully.",
        "filename": file.filename,
    }
