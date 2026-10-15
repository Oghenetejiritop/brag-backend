
"""
BRAG Configuration Module

This file centralizes all system-wide configuration values.
It prepares BRAG for:
- Multi-user support
- Multiple environments (dev/prod)
- Billing tiers (future Phase 7)
- LLM provider flexibility
"""
# =============================================================================
# Default Configuration
# These values centralize the RAG configuration and avoid hardcoded "magic
# numbers" throughout the codebase.
# =============================================================================

DEFAULT_CHUNK_SIZE = 500
DEFAULT_CHUNK_OVERLAP = 150

DEFAULT_RETRIEVAL_K = 4
DEFAULT_FETCH_K = 20

DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TEMPERATURE = 0


DEFAULT_SYSTEM_PROMPT = """
You are a helpful assistant that answers questions using only the provided context.

Instructions:
- Use only information from the retrieved context.
- If the user asks for a summary, overview, explanation, or description,
  summarize the retrieved context.
- If the answer is not present in the context, reply:
  "I don't know based on the provided information."
- Do not use outside knowledge or invent facts.

Context:
{context}

Question:
{question}
"""

# =============================================================================
# Default Knowledge Base
# =============================================================================

DEFAULT_DOCUMENT_PATH = "sample.pdf"
DEFAULT_VECTOR_STORE_PATH = "chroma_db"

# ==========================================================
# Supported document types.
#
# Future phases will expand this list as BRAG gains support
# for additional document loaders.
# ==========================================================

SUPPORTED_DOCUMENT_EXTENSIONS = {
    ".pdf",
}


# =============================================================================
# Relational Database Configuration
# =============================================================================

# SQLite is used during local development because it requires no separate
# database server. SQLAlchemy allows this URL to be replaced with PostgreSQL
# or MySQL configuration during a future production migration.
DATABASE_URL = "sqlite:///./brag.db"



# Browser origins permitted to call BRAG from the React frontend.
# Set BRAG_CORS_ORIGINS to comma-separated, explicit origins in deployment.
# No wildcard origins are permitted.
import os

_DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)

def get_cors_origins() -> list[str]:
    """Return exact, validated origins for browser cross-origin requests."""
    raw = os.getenv("BRAG_CORS_ORIGINS")
    if raw is None:
        return list(_DEFAULT_CORS_ORIGINS)

    origins = [origin.strip().rstrip("/") for origin in raw.split(",") if origin.strip()]
    for origin in origins:
        if origin == "*" or not origin.startswith(("http://", "https://")):
            raise ValueError("BRAG_CORS_ORIGINS must contain explicit HTTP(S) origins.")
        # Origins cannot include a path, query, or fragment.
        from urllib.parse import urlsplit
        parsed = urlsplit(origin)
        if not parsed.netloc or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise ValueError("BRAG_CORS_ORIGINS contains an invalid origin.")
    return list(dict.fromkeys(origins))
