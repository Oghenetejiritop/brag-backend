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
        self._rag_service: RAGService | None = RAGService()

    def initialize_from_file(self, file_path: str):
        self._rag_service.initialize_from_file(file_path)

    def get_service(self) -> RAGService:
        if not self._rag_service:
            raise ValueError("RAG service not initialized")
        return self._rag_service

    def has_service(self) -> bool:
        return self._rag_service is not None
