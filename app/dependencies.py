from typing import Optional

from app.services.rag_service import RAGService


class RAGManager:
    """
    Manages the active RAG service instance.

    During Phase 3 there is only one active knowledge base.

    Later this manager will evolve to support multiple users,
    each with their own RAG service.
    """

    def __init__(self):
        self._rag_service: Optional[RAGService] = None

    def set_service(self, rag_service: RAGService) -> None:
        """
        Register the active RAG service.
        """
        self._rag_service = rag_service

    def get_service(self) -> Optional[RAGService]:
        """
        Return the active RAG service.

        Returns:
            The configured RAG service or None if no
            knowledge base has been uploaded.
        """
        return self._rag_service

    def has_service(self) -> bool:
        """
        Indicates whether a knowledge base has been loaded.
        """
        return self._rag_service is not None


rag_manager = RAGManager()