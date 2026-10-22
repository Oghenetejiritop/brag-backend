"""Offline regression checks; run alongside the existing BRAG suite."""
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.config import CHATBOT_SYSTEM_MESSAGE
from app.services.rag_service import RAGService


def test_authoritative_system_message():
    assert "{assistant_name}" in CHATBOT_SYSTEM_MESSAGE
    assert "{assistant_description}" in CHATBOT_SYSTEM_MESSAGE
    assert "other assistants" in CHATBOT_SYSTEM_MESSAGE


def test_context_finds_name_in_later_page_without_page_hint():
    service = object.__new__(RAGService)
    chunks = [
        ("A general introduction.", {"source": "resume.pdf", "page": 0}),
        ("Oghenetejiri built accessible applications.", {"source": "resume.pdf", "page": 19}),
    ]
    collection = MagicMock()
    collection.count.return_value = len(chunks)
    collection.get.return_value = {
        "documents": [t for t, _ in chunks],
        "metadatas": [m for _, m in chunks],
    }
    service._vector_store = SimpleNamespace(_collection=collection)
    context = service._build_chatbot_context("Do you know Oghenetejiri?", [])
    assert "Oghenetejiri" in context
    assert "page: 20" in context


def test_context_uses_only_attached_store():
    service = object.__new__(RAGService)
    collection = MagicMock()
    collection.count.return_value = 1
    collection.get.return_value = {
        "documents": ["George's private knowledge"],
        "metadatas": [{"source": "george.pdf", "page": 0}],
    }
    service._vector_store = SimpleNamespace(_collection=collection)
    context = service._build_chatbot_context("Tell me your information", [])
    assert "George's private knowledge" in context
    assert "c3po.pdf" not in context.lower()
