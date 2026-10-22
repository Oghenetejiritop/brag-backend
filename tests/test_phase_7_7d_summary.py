
"""Regression checks for the current MVP RAG architecture.

Replaces tests for the removed _answer_summary private API. These tests
verify retrieval and routing without calling OpenAI or modifying storage.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.config import CHATBOT_MAX_CONTEXT_CHARS, CHATBOT_SYSTEM_MESSAGE
from app.services.rag_service import RAGService


def _service(chunks):
    service = object.__new__(RAGService)
    collection = MagicMock()
    collection.count.return_value = len(chunks)

    def get(*, limit, offset, include):
        batch = chunks[offset:offset + limit]
        return {
            "documents": [item["text"] for item in batch],
            "metadatas": [item["meta"] for item in batch],
        }

    collection.get.side_effect = get
    service._vector_store = SimpleNamespace(_collection=collection)
    return service


def test_multi_document_summary_uses_both_sources_without_clarification():
    service = _service([
        {"text": "Alpha guidance for apprentices", "meta": {"source": "one.pdf", "page": 0}},
        {"text": "Beta guidance for mentors", "meta": {"source": "two.pdf", "page": 4}},
    ])
    context = service._build_chatbot_context("Summarize the uploaded documents", [])
    assert "Alpha guidance for apprentices" in context
    assert "Beta guidance for mentors" in context
    assert "one.pdf" in context and "two.pdf" in context
    assert "Which document" not in context


def test_later_page_can_be_found_without_page_number():
    service = _service([
        {"text": "First page introduction", "meta": {"source": "one.pdf", "page": 0}},
        {"text": "The unique cobalt telescope was repaired", "meta": {"source": "one.pdf", "page": 8}},
    ])
    context = service._build_chatbot_context("Who repaired the cobalt telescope?", [])
    assert "unique cobalt telescope" in context
    assert "page: 9" in context


def test_large_document_context_is_bounded_not_misrepresented_as_complete():
    service = _service([
        {"text": "A" * 37000, "meta": {"source": "long.pdf", "page": 7}},
    ])
    context = service._build_chatbot_context("Summarize the document", [])
    assert len(context) <= CHATBOT_MAX_CONTEXT_CHARS
    assert "A" * 37000 not in context
    # This is a safety bound, NOT a guarantee of a complete long-PDF summary.


def test_chatbot_question_routes_through_assistant_scoped_context():
    service = _service([
        {"text": "Private assistant-specific fact", "meta": {"source": "private.pdf", "page": 2}},
    ])
    service._rag_chain = object()
    service._retriever = MagicMock()
    service._retriever.invoke.return_value = []
    service._generate_grounded_answer = MagicMock(return_value="Grounded answer")
    assert service.answer_question("What do you know?", assistant_name="George") == "Grounded answer"
    kwargs = service._generate_grounded_answer.call_args.kwargs
    assert kwargs["assistant_name"] == "George"
    assert "Private assistant-specific fact" in kwargs["context"]
    service._retriever.invoke.assert_called_once_with("What do you know?")


def test_system_message_separates_identity_from_document_facts():
    assert "{assistant_name}" in CHATBOT_SYSTEM_MESSAGE
    assert "{assistant_description}" in CHATBOT_SYSTEM_MESSAGE
    assert "other assistants" in CHATBOT_SYSTEM_MESSAGE
    assert "I don't know based on the provided information." in CHATBOT_SYSTEM_MESSAGE
