from pathlib import Path

from fastapi import UploadFile

from app.core.config import SUPPORTED_DOCUMENT_EXTENSIONS


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

    def __init__(self, upload_directory: str = "uploads") -> None:
        """
        Initialize the upload service.

        Args:
            upload_directory:
                Directory where uploaded files will be stored.
        """

        self._upload_directory = Path(upload_directory)

        # -------------------------------------------------------------
        # Ensure the upload directory exists.
        # This allows BRAG to start cleanly even on a new machine.
        # -------------------------------------------------------------
        self._upload_directory.mkdir(
            parents=True,
            exist_ok=True,
        )


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
            ValueError:
                If the uploaded document type is unsupported.
        """

        extension = Path(file.filename).suffix.lower()

        if extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
            supported = ", ".join(
                sorted(SUPPORTED_DOCUMENT_EXTENSIONS)
            )

            raise ValueError(
                f"Unsupported document type '{extension}'. "
                f"Supported types: {supported}"
            )

    async def save_file(
        self,
        file: UploadFile,
    ) -> str:
        """
        Save an uploaded file to disk.

        Args:
            file:
                Uploaded file received by FastAPI.

        Returns:
            Absolute path to the saved file.
        """

        # -------------------------------------------------------------
        # Reject unsupported document types before writing to disk.
        # -------------------------------------------------------------
        self._validate_file_type(file)

        file_path = self._upload_directory / file.filename

        # -------------------------------------------------------------
        # Read the uploaded file and persist it.
        # Using Path keeps the implementation platform-independent.
        # -------------------------------------------------------------
        contents = await file.read()

        with file_path.open("wb") as destination:
            destination.write(contents)

        return str(file_path)

