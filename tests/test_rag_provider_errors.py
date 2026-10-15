
"""Isolated tests for BRAG RAG provider error translation."""
from unittest.mock import Mock

import pytest
from openai import APIConnectionError

from app.exceptions.rag_exceptions import RAGProviderUnavailableError
from app.services.rag_service import RAGService


def make_service(chain: Mock | None) -> RAGService:
    service = RAGService.__new__(RAGService)
    service._rag_chain = chain
    service._logger = Mock()
    return service


def test_successful_answer() -> None:
    chain = Mock()
    chain.invoke.return_value = "The purple elephant plays Python chess."
    assert make_service(chain).answer_question("Test?") == "The purple elephant plays Python chess."


def test_connection_error_is_translated() -> None:
    chain = Mock()
    chain.invoke.side_effect = APIConnectionError(message="private details", request=Mock())
    with pytest.raises(RAGProviderUnavailableError, match="temporarily unavailable"):
        make_service(chain).answer_question("Test?")


def test_unexpected_errors_remain_visible_to_developers() -> None:
    chain = Mock()
    chain.invoke.side_effect = RuntimeError("Unexpected bug")
    with pytest.raises(RuntimeError, match="Unexpected bug"):
        make_service(chain).answer_question("Test?")


def test_uninitialized_pipeline_is_rejected() -> None:
    with pytest.raises(ValueError, match="not been initialized"):
        make_service(None).answer_question("Test?")
