
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

DEFAULT_CHUNK_SIZE = 1000
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
