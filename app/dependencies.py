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

        # Cache chatbot-specific RAG services separately
        # from the legacy user-level RAG registry.
        self._chatbot_services: dict[
            tuple[str, str],
            RAGService,
        ] = {}

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

    def initialize_chatbot_from_file(
        self,
        file_path: str,
        user_id: str,
        chatbot_id: str,
    ) -> None:
        """
        Initialize a chatbot's RAG service from a document.

        The caller must verify chatbot ownership and active
        status before invoking this method.

        Args:
            file_path:
                Path to an uploaded document.
            user_id:
                Public UUID of the authenticated owner.
            chatbot_id:
                Public UUID of the chatbot.
        """
        rag_service = RAGService()

        # This method requires chatbot-specific ingestion.
        # It will be connected to the upload workflow
        # during Phase 5.7.
        raise NotImplementedError(
            "Chatbot-specific document ingestion "
            "will be implemented in Phase 5.7."
        )

    def reconstruct_chatbot(
        self,
        user_id: str,
        chatbot_id: str,
    ) -> RAGService:
        """
        Reconstruct and cache a chatbot's RAG service.

        The caller must verify chatbot ownership and active
        status before invoking this method.

        Args:
            user_id:
                Public UUID of the authenticated owner.
            chatbot_id:
                Public UUID of the chatbot.

        Returns:
            Reconstructed RAGService instance.
        """
        cache_key = (user_id, chatbot_id)

        # Avoid rebuilding an already initialized pipeline.
        existing_service = self._chatbot_services.get(
            cache_key
        )

        if existing_service is not None:
            return existing_service

        rag_service = RAGService()

        rag_service.initialize_from_existing_store(
            user_id=user_id,
            chatbot_id=chatbot_id,
        )

        # Only cache the service after reconstruction succeeds.
        self._chatbot_services[cache_key] = rag_service

        return rag_service

    def get_chatbot_service(
        self,
        user_id: str,
        chatbot_id: str,
    ) -> RAGService:
        """
        Return a previously initialized chatbot RAG service.

        Raises:
            ValueError:
                If the chatbot has no cached RAG service.
        """
        cache_key = (user_id, chatbot_id)

        rag_service = self._chatbot_services.get(
            cache_key
        )

        if rag_service is None:
            raise ValueError(
                "No RAG service initialized for this chatbot."
            )

        return rag_service

    def has_chatbot_service(
        self,
        user_id: str,
        chatbot_id: str,
    ) -> bool:
        """
        Return whether a chatbot has a cached RAG service.
        """
        cache_key = (user_id, chatbot_id)

        return cache_key in self._chatbot_services


#Expose services
model_service = ModelService()
rag_manager = RAGManager()
upload_service = UploadService()