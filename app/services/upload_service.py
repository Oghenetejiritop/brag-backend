
from pathlib import (
    Path,
    )

from uuid import uuid4

from fastapi import UploadFile

from app.core.config import (
    SUPPORTED_DOCUMENT_EXTENSIONS,
    MAX_UPLOAD_SIZE_BYTES
)

from app.exceptions.upload_exceptions import (
    EmptyFilenameError,
    FileTooLargeError,
    UnsupportedDocumentTypeError,
)

from app.services.workspace_service import WorkspaceService


class UploadService:
    """
    Handles document uploads for BRAG.

    Responsibilities:
        - Ensure the upload directory exists.
        - Persist uploaded files to disk.
        - Return the saved file path.

    Future enhancements:
        - File type validation.
        - File size limits.
        - Virus scanning.
        - Cloud storage (AWS S3, Azure Blob Storage).
        - Duplicate detection.
    """

    def __init__(self) -> None:
        """
        Initialize the upload service.

        Workspace management is delegated to WorkspaceService.
        """

        self._workspace_service = WorkspaceService()

    def _validate_file_type(
        self,
        file: UploadFile,
    ) -> None:
        """
        Validate that the uploaded document type is supported.

        Args:
            file:
                Uploaded file received by FastAPI.

        Raises:
            UnsupportedDocumentTypeError:
                If the uploaded document type is unsupported.
        """

        extension = Path(file.filename).suffix.lower()

        if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
            supported = ", ".join(
                sorted(SUPPORTED_DOCUMENT_EXTENSIONS)
            )

            raise UnsupportedDocumentTypeError(
                f"Unsupported document type '{extension}'. "
                f"Supported types: {supported}"
            )

    def _generate_unique_filename(
        self,
        original_filename: str,
    ) -> str:
        """
        Generate a unique filename while preserving the original name.

        A UUID prefix prevents filename collisions when multiple users
        upload documents with identical names.

        Args:
            original_filename:
                The filename provided by the client.

        Returns:
            A unique filename suitable for storage.
        """

        unique_id = uuid4().hex

        return f"{unique_id}_{original_filename}"

    async def save_file(self, user_id: str, file: UploadFile) -> str:
        """Save a legacy user upload using the same 10 MiB policy as chatbots."""
        if not file.filename:
            raise EmptyFilenameError("Uploaded file must have a filename.")

        safe_filename = self._safe_filename(file.filename)
        if not safe_filename or safe_filename in {".", ".."}:
            raise EmptyFilenameError("Uploaded file must have a valid filename.")

        self._validate_file_type(file)
        unique_filename = self._generate_unique_filename(safe_filename)
        upload_directory = self._workspace_service.get_upload_directory(user_id)
        file_path = upload_directory / unique_filename

        max_bytes = MAX_UPLOAD_SIZE_BYTES
        chunk_size = 1024 * 1024
        total_bytes = 0
        try:
            with file_path.open("xb") as destination:
                while chunk := await file.read(chunk_size):
                    total_bytes += len(chunk)
                    if total_bytes > max_bytes:
                        raise FileTooLargeError(
                            "Uploaded file exceeds the 10 MiB limit."
                        )
                    destination.write(chunk)
        except Exception:
            file_path.unlink(missing_ok=True)
            raise

        return str(file_path)


    @staticmethod
    def _safe_filename(filename: str) -> str:
        """Remove directory components from an uploaded filename."""
        normalized = filename.replace("\\", "/")
        return Path(normalized).name


    async def save_chatbot_file(
        self,
        user_id: str,
        chatbot_id: str,
        file: UploadFile,
    ) -> str:
        """Save a document inside an isolated chatbot workspace."""
        if not file.filename:
            raise EmptyFilenameError(
                "Uploaded file must have a filename."
            )

        safe_filename = self._safe_filename(file.filename)

        if not safe_filename or safe_filename in {".", ".."}:
            raise EmptyFilenameError(
                "Uploaded file must have a valid filename."
            )

        self._validate_file_type(file)

        unique_filename = self._generate_unique_filename(
            safe_filename
        )

        upload_directory = (
            self._workspace_service.get_chatbot_upload_directory(
                user_id=user_id,
                chatbot_id=chatbot_id,
            )
        )

        file_path = upload_directory / unique_filename

        # Limit each uploaded file to 10 MiB.
        max_bytes = MAX_UPLOAD_SIZE_BYTES
        chunk_size = 1024 * 1024
        total_bytes = 0

        try:
            with file_path.open("xb") as destination:
                while chunk := await file.read(chunk_size):
                    total_bytes += len(chunk)

                    if total_bytes > max_bytes:
                        raise FileTooLargeError(
                            "Uploaded file exceeds the 10 MiB limit."
                        )

                    destination.write(chunk)

        except Exception:
            file_path.unlink(missing_ok=True)
            raise

        return str(file_path)
