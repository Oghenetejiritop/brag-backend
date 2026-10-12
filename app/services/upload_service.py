from pathlib import (
    Path,
    PureWindowsPath
    )

from uuid import uuid4

from fastapi import UploadFile

from app.core.config import SUPPORTED_DOCUMENT_EXTENSIONS

from app.exceptions.upload_exceptions import (
    EmptyFilenameError,
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

    async def save_file(
        self,
        user_id: str,
        file: UploadFile,
    ) -> str:
        """
        Save an uploaded file to disk.

        Args:
        user_id:
        Identifier of the active user.

                    file:
                Uploaded file received by FastAPI.

            Raises:
            EmptyFilenameError
            UnsupportedDocumentTypeError
            
        Returns:
            Absolute path to the saved file.
        """

        if not file.filename:
            raise EmptyFilenameError(
            "Uploaded file must have a filename."
            )

        # -------------------------------------------------------------
        # Reject unsupported document types before writing to disk.
        # -------------------------------------------------------------
        self._validate_file_type(file)

        # Generate a unique filename to avoid overwriting existing
        # documents that share the same original name.
        unique_filename = self._generate_unique_filename(file.filename)

        # Retrieve the user's dedicated upload directory.
        # WorkspaceService ensures the directory exists.
        upload_directory = self._workspace_service.get_upload_directory(
            user_id
        )

        file_path = upload_directory / unique_filename

        # -------------------------------------------------------------
        # Read the uploaded file and persist it.
        # Using Path keeps the implementation platform-independent.
        contents = await file.read()

        with file_path.open("wb") as destination:
            destination.write(contents)

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
        max_bytes = 10 * 1024 * 1024
        chunk_size = 1024 * 1024
        total_bytes = 0

        try:
            with file_path.open("xb") as destination:
                while chunk := await file.read(chunk_size):
                    total_bytes += len(chunk)

                    if total_bytes > max_bytes:
                        raise ValueError(
                            "Uploaded file exceeds the 10 MiB limit."
                        )

                    destination.write(chunk)

        except Exception:
            file_path.unlink(missing_ok=True)
            raise

        return str(file_path)
