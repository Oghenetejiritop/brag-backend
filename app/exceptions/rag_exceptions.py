"""RAG domain errors independent of HTTP transport."""


class RAGError(Exception):
    """Base exception for RAG failures."""


class RAGProviderUnavailableError(RAGError):
    """External AI provider is temporarily unavailable."""
