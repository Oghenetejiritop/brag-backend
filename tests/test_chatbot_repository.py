
"""
Repository tests for persistent BRAG chatbots.

These tests verify chatbot creation, lookup, listing, and
ownership-scoped retrieval without modifying the production
BRAG database.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine, event
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)

from app.db.database import Base
from app.db.models.user import User
from app.repositories.chatbot_repository import (
    ChatbotRepository,
)


def test_chatbot_repository() -> None:
    """
    Verify persistent chatbot repository operations.
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
            # -----------------------------------------------------
            # Create two independent owners so ownership-scoped
            # repository behavior can be validated.
            # -----------------------------------------------------
            user_a = User()
            user_b = User()

            database_session.add_all(
                [
                    user_a,
                    user_b,
                ]
            )

            database_session.commit()

            database_session.refresh(
                user_a
            )
            database_session.refresh(
                user_b
            )

            repository = ChatbotRepository(
                database_session=database_session
            )

            # -----------------------------------------------------
            # Create multiple chatbots for User A and one for B.
            # -----------------------------------------------------
            chatbot_a_one = repository.create(
                user_db_id=user_a.id,
                name="HR Assistant",
                description=(
                    "Answers HR policy questions."
                ),
            )

            chatbot_a_two = repository.create(
                user_db_id=user_a.id,
                name="Product Assistant",
            )

            chatbot_b = repository.create(
                user_db_id=user_b.id,
                name="Support Assistant",
            )

            assert chatbot_a_one.id is not None
            assert chatbot_a_one.chatbot_id

            print(
                "PASS: Repository created "
                "persistent chatbots."
            )

            # -----------------------------------------------------
            # Internal primary-key lookup.
            # -----------------------------------------------------
            retrieved_by_id = (
                repository.get_by_id(
                    chatbot_a_one.id
                )
            )

            assert retrieved_by_id is not None

            assert (
                retrieved_by_id.chatbot_id
                == chatbot_a_one.chatbot_id
            )

            print(
                "PASS: Internal chatbot ID "
                "lookup validated."
            )

            # -----------------------------------------------------
            # Public UUID lookup.
            # -----------------------------------------------------
            retrieved_by_public_id = (
                repository.get_by_chatbot_id(
                    chatbot_a_one.chatbot_id
                )
            )

            assert retrieved_by_public_id is not None

            assert (
                retrieved_by_public_id.id
                == chatbot_a_one.id
            )

            print(
                "PASS: Public chatbot UUID "
                "lookup validated."
            )

            # -----------------------------------------------------
            # User-scoped listing.
            # -----------------------------------------------------
            user_a_chatbots = (
                repository.get_by_user_id(
                    user_a.id
                )
            )

            user_a_chatbot_ids = {
                chatbot.chatbot_id
                for chatbot in user_a_chatbots
            }

            assert len(user_a_chatbots) == 2

            assert chatbot_a_one.chatbot_id in (
                user_a_chatbot_ids
            )

            assert chatbot_a_two.chatbot_id in (
                user_a_chatbot_ids
            )

            assert chatbot_b.chatbot_id not in (
                user_a_chatbot_ids
            )

            print(
                "PASS: User chatbot listing "
                "is ownership scoped."
            )

            # -----------------------------------------------------
            # Correct ownership must return the chatbot.
            # -----------------------------------------------------
            owned_chatbot = (
                repository
                .get_by_chatbot_id_and_user_id(
                    public_chatbot_id=(
                        chatbot_a_one.chatbot_id
                    ),
                    user_db_id=user_a.id,
                )
            )

            assert owned_chatbot is not None

            assert (
                owned_chatbot.id
                == chatbot_a_one.id
            )

            print(
                "PASS: Correct chatbot ownership "
                "lookup validated."
            )

            # -----------------------------------------------------
            # User B must not retrieve User A's chatbot through
            # the ownership-scoped repository operation.
            # -----------------------------------------------------
            cross_user_result = (
                repository
                .get_by_chatbot_id_and_user_id(
                    public_chatbot_id=(
                        chatbot_a_one.chatbot_id
                    ),
                    user_db_id=user_b.id,
                )
            )

            assert cross_user_result is None

            print(
                "PASS: Cross-user chatbot lookup "
                "was rejected."
            )

            # -----------------------------------------------------
            # Unknown public UUIDs should return None rather than
            # raising a persistence-layer exception.
            # -----------------------------------------------------
            missing_chatbot = (
                repository.get_by_chatbot_id(
                    "00000000-0000-0000-0000-000000000000"
                )
            )

            assert missing_chatbot is None

            print(
                "PASS: Missing chatbot lookup "
                "returns None."
            )

            print(
                "PASS: Chatbot repository "
                "validation completed."
            )

        finally:
            database_session.close()

            Base.metadata.drop_all(
                bind=test_engine
            )

            test_engine.dispose()


if __name__ == "__main__":
    test_chatbot_repository()
