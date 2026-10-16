
import os


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
DATABASE_URL = os.getenv("BRAG_DATABASE_URL", "sqlite:///./brag.db")



# Browser origins permitted to call BRAG from the React frontend.
# Set BRAG_CORS_ORIGINS to comma-separated, explicit origins in deployment.
# No wildcard origins are permitted.
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


# Deployment checks run at FastAPI startup, not at module import.
# This preserves the existing local development and test workflows.
def get_brag_environment() -> str:
    """Return a supported BRAG environment name."""
    environment = os.getenv("BRAG_ENV", "development").strip().lower()
    if environment not in {"development", "testing", "production"}:
        raise ValueError("BRAG_ENV must be development, testing, or production.")
    return environment


def validate_environment() -> None:
    """Reject unsafe production settings without disclosing secret values."""
    environment = get_brag_environment()
    origins = get_cors_origins()
    if environment != "production":
        return

    if not os.getenv("OPENAI_API_KEY", "").strip():
        raise ValueError("Production requires OPENAI_API_KEY.")
    if not os.getenv("BRAG_CORS_ORIGINS", "").strip() or not origins:
        raise ValueError("Production requires explicit BRAG_CORS_ORIGINS.")
    if any(not origin.startswith("https://") for origin in origins):
        raise ValueError("Production CORS origins must use HTTPS.")
    if not os.getenv("BRAG_DATABASE_URL", "").strip():
        raise ValueError("Production requires BRAG_DATABASE_URL.")
    if DATABASE_URL.startswith("sqlite:"):
        raise ValueError("Production requires a non-SQLite database URL.")


def get_api_documentation_settings() -> dict[str, str | None]:
    """Disable interactive API documentation in production by default.

    Authentication remains enforced independently of documentation visibility.
    """
    if get_brag_environment() == "production":
        return {"docs_url": None, "redoc_url": None, "openapi_url": None}
    return {"docs_url": "/docs", "redoc_url": "/redoc", "openapi_url": "/openapi.json"}
