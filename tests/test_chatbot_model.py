
"""
Persistence tests for the BRAG Chatbot model.

These tests verify the foundational ownership relationship
between persistent users and chatbots.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, event
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)

from app.db.database import Base
from app.db.models.chatbot import Chatbot
from app.db.models.user import User


def test_chatbot_model() -> None:
    """
    Verify persistent chatbot creation and user ownership.
    """

    with TemporaryDirectory() as temporary_directory:
        database_path = (
            Path(temporary_directory)
            / "brag_test.db"
        )

        database_url = (
            f"sqlite:///{database_path.as_posix()}"
        )

        test_engine = create_engine(
            database_url,
            connect_args={
                "check_same_thread": False,
            },
        )

        @event.listens_for(
            test_engine,
            "connect",
        )
        def enable_foreign_keys(
            database_connection,
            connection_record,
        ) -> None:
            """
            Enable SQLite foreign-key enforcement.
            """

            del connection_record

            cursor = database_connection.cursor()

            try:
                cursor.execute(
                    "PRAGMA foreign_keys=ON"
                )
            finally:
                cursor.close()

        TestSessionLocal = sessionmaker(
            bind=test_engine,
            autoflush=False,
            expire_on_commit=False,
        )

        Base.metadata.create_all(
            bind=test_engine
        )

        database_session: Session = (
            TestSessionLocal()
        )

        try:
            user = User()

            database_session.add(user)
            database_session.commit()
            database_session.refresh(user)

            chatbot = Chatbot(
                user_id=user.id,
                name="Test Assistant",
                description=(
                    "Chatbot used to validate "
                    "persistent ownership."
                ),
            )

            database_session.add(chatbot)
            database_session.commit()
            database_session.refresh(chatbot)

            assert chatbot.id is not None
            assert chatbot.chatbot_id
            assert chatbot.user_id == user.id
            assert chatbot.name == "Test Assistant"
            assert chatbot.is_active is True

            assert chatbot.user.id == user.id
            assert chatbot in user.chatbots

            print(
                "PASS: Persistent chatbot created."
            )

            print(
                "PASS: Chatbot received a public UUID."
            )

            print(
                "PASS: Chatbot belongs to the correct user."
            )

            print(
                "PASS: User-to-chatbot relationship validated."
            )

        finally:
            database_session.close()

            Base.metadata.drop_all(
                bind=test_engine
            )

            test_engine.dispose()


if __name__ == "__main__":
    test_chatbot_model()
