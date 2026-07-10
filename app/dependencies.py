
from app.services.model_service import ModelService
from app.services.rag_service import RAGService
from app.services.upload_service import UploadService


class RAGManager:
    """
    Manages active RAG service instances.

    During Phase 4, each user receives an independent RAGService.

    This prevents users from sharing vector stores,
    retrievers, and chat pipelines.
    """

    def __init__(self) -> None:
        """
        Initialize the RAG manager.
        """

        # -------------------------------------------------------------
        # Maps a user ID to that user's active RAGService.
        # -------------------------------------------------------------
        self._services: dict[str, RAGService] = {}

    def initialize_from_file(
        self,
        file_path: str,
        user_id: str
    ) -> None:
        """
        Create or replace the user's active RAG service.

        Args:
            file_path:
                Uploaded document path.

                            user_id:
                Temporary user identifier.

        """

        rag_service = RAGService()

        rag_service.initialize_from_file(
            file_path=file_path,
            user_id=user_id
            )

        self._services[user_id] = rag_service

    def get_service(
        self,
        user_id: str,
    ) -> RAGService:
        """
        Retrieve the active RAG service for a user.

        Raises:
            ValueError:
                If the user has not uploaded a document.
        """

        if user_id not in self._services:
            raise ValueError(
                "No RAG service initialized for this user."
            )

        return self._services[user_id]

    def has_service(
        self,
        user_id: str,
    ) -> bool:
        """
        Determine whether the user has an active RAG service.
        """

        return user_id in self._services


# Expose services
model_service = ModelService()
rag_manager = RAGManager()
upload_service = UploadService()