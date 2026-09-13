from app.services.model_service import ModelService
from app.services.rag_service import RAGService
from app.services.upload_service import UploadService


class RAGManager:
    """
    Manage active user-specific RAG service instances.

    Each authenticated BRAG user receives an independent
    RAGService instance. This prevents users from sharing
    vector stores, retrievers, and RAG chains.

    Important:
        The active service registry is currently stored in memory.
        It is therefore cleared when the application process
        restarts. Persistent RAG reconstruction will be addressed
        as BRAG introduces persistent chatbot and knowledge-base
        resources.
    """

    def __init__(self) -> None:
        """
        Initialize an empty in-memory RAG service registry.
        """

        self._services: dict[str, RAGService] = {}

    def initialize_from_file(
        self,
        file_path: str,
        user_id: str,
    ) -> None:
        """
        Create or replace a user's active RAG service.

        Args:
            file_path:
                Path to the authenticated user's uploaded document.

            user_id:
                Persistent public UUID of the authenticated user.
        """

        rag_service = RAGService()

        rag_service.initialize_from_file(
            file_path=file_path,
            user_id=user_id,
        )

        self._services[user_id] = rag_service

    def get_service(
        self,
        user_id: str,
    ) -> RAGService:
        """
        Return a user's active RAG service.

        Args:
            user_id:
                Persistent public UUID of the authenticated user.

        Returns:
            The user's active RAGService.

        Raises:
            ValueError:
                If no active RAG service exists for the user.
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
        Return whether a user has an active RAG service.
        """

        return user_id in self._services


#Expose services
model_service = ModelService()
rag_manager = RAGManager()
upload_service = UploadService()