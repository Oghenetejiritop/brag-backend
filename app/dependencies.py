
from app.core.config import (
    DEFAULT_DOCUMENT_PATH,
    DEFAULT_VECTOR_STORE_PATH,
)

from app.services.rag_service import RAGService


# Singleton instance shared by the application.
#
# During Phase 3 we are using a single knowledge base.
# Later, in the multi-user phase, this will be replaced
# by user-specific RAG services.
rag_service = RAGService(
    document_path = DEFAULT_DOCUMENT_PATH,
    persist_directory = DEFAULT_VECTOR_STORE_PATH
)

