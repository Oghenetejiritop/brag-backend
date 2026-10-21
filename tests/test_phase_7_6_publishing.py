
"""Publishing regression checks (run with existing BRAG pytest suite)."""
from unittest.mock import MagicMock
from app.db.models.chatbot import Chatbot
from app.repositories.chatbot_repository import ChatbotRepository


def test_new_chatbot_private_by_default():
    assistant = Chatbot(user_id=1, name="Private assistant")
    # SQLAlchemy column default is applied at INSERT, not construction.
    assert Chatbot.__table__.c.is_published.default.arg is False
    assert Chatbot.__table__.c.is_published.server_default is not None


def test_publish_commits_and_refreshes():
    session = MagicMock()
    assistant = Chatbot(user_id=1, name="Assistant")
    result = ChatbotRepository(session).set_published(assistant, True)
    assert result.is_published is True
    session.commit.assert_called_once()
    session.refresh.assert_called_once_with(assistant)


def test_unpublish_commits():
    session = MagicMock()
    assistant = Chatbot(user_id=1, name="Assistant", is_published=True)
    result = ChatbotRepository(session).set_published(assistant, False)
    assert result.is_published is False
    session.commit.assert_called_once()


def test_failed_publish_rolls_back():
    session = MagicMock()
    session.commit.side_effect = RuntimeError("database failure")
    assistant = Chatbot(user_id=1, name="Assistant")
    try:
        ChatbotRepository(session).set_published(assistant, True)
    except RuntimeError:
        pass
    else:
        raise AssertionError("Expected database failure")
    session.rollback.assert_called_once()
