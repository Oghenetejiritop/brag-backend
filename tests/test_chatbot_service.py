

"""
Business-rule tests for BRAG ChatbotService.

These tests validate chatbot creation, normalization, ownership,
deactivation, and tenant isolation using a temporary database.
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
from app.exceptions.chatbot_exceptions import (
    ChatbotNotFoundError,
    InactiveChatbotError,
    InactiveChatbotOwnerError,
    InvalidChatbotNameError,
)
from app.services.chatbot_service import ChatbotService


def test_chatbot_service() -> None:
    """
    Verify ChatbotService business and ownership rules.
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
            user_a = User()
            user_b = User()

            database_session.add_all(
                [
                    user_a,
                    user_b,
                ]
            )

            database_session.commit()

            database_session.refresh(user_a)
            database_session.refresh(user_b)

            service = ChatbotService(
                database_session=database_session
            )

            # -----------------------------------------------------
            # Creation and input normalization.
            # -----------------------------------------------------
            chatbot = service.create_chatbot(
                user=user_a,
                name="  HR Assistant  ",
                description=(
                    "  Answers employee questions.  "
                ),
            )

            assert chatbot.user_id == user_a.id
            assert chatbot.name == "HR Assistant"
            assert (
                chatbot.description
                == "Answers employee questions."
            )
            assert chatbot.is_active is True

            print(
                "PASS: Chatbot creation and "
                "normalization validated."
            )

            # -----------------------------------------------------
            # Empty chatbot names must be rejected.
            # -----------------------------------------------------
            try:
                service.create_chatbot(
                    user=user_a,
                    name="   ",
                )

            except InvalidChatbotNameError:
                pass

            else:
                raise AssertionError(
                    "Empty chatbot name was accepted."
                )

            print(
                "PASS: Invalid chatbot name "
                "was rejected."
            )

            # -----------------------------------------------------
            # Correct owner can retrieve the chatbot.
            # -----------------------------------------------------
            owned_chatbot = service.get_chatbot(
                user=user_a,
                public_chatbot_id=(
                    chatbot.chatbot_id
                ),
            )

            assert owned_chatbot.id == chatbot.id

            print(
                "PASS: Chatbot owner retrieval "
                "validated."
            )

            # -----------------------------------------------------
            # Another user must not be able to retrieve it.
            # -----------------------------------------------------
            try:
                service.get_chatbot(
                    user=user_b,
                    public_chatbot_id=(
                        chatbot.chatbot_id
                    ),
                )

            except ChatbotNotFoundError:
                pass

            else:
                raise AssertionError(
                    "Cross-user chatbot access "
                    "was allowed."
                )

            print(
                "PASS: Cross-user chatbot access "
                "was rejected."
            )

            # -----------------------------------------------------
            # User listing must remain ownership scoped.
            # -----------------------------------------------------
            service.create_chatbot(
                user=user_a,
                name="Product Assistant",
            )

            service.create_chatbot(
                user=user_b,
                name="Support Assistant",
            )

            user_a_chatbots = (
                service.get_user_chatbots(
                    user=user_a
                )
            )

            assert len(user_a_chatbots) == 2

            assert all(
                item.user_id == user_a.id
                for item in user_a_chatbots
            )

            print(
                "PASS: User chatbot listing "
                "is ownership scoped."
            )

            # -----------------------------------------------------
            # Deactivation must persist without deleting the record.
            # -----------------------------------------------------
            deactivated_chatbot = (
                service.deactivate_chatbot(
                    user=user_a,
                    public_chatbot_id=(
                        chatbot.chatbot_id
                    ),
                )
            )

            assert (
                deactivated_chatbot.is_active
                is False
            )

            print(
                "PASS: Chatbot deactivation "
                "validated."
            )

            # -----------------------------------------------------
            # Normal active-only retrieval must reject an inactive
            # chatbot.
            # -----------------------------------------------------
            try:
                service.get_chatbot(
                    user=user_a,
                    public_chatbot_id=(
                        chatbot.chatbot_id
                    ),
                )

            except InactiveChatbotError:
                pass

            else:
                raise AssertionError(
                    "Inactive chatbot was treated "
                    "as active."
                )

            # The record must still be available when an operation
            # explicitly allows inactive chatbots.
            persisted_chatbot = (
                service.get_chatbot(
                    user=user_a,
                    public_chatbot_id=(
                        chatbot.chatbot_id
                    ),
                    require_active=False,
                )
            )

            assert persisted_chatbot.id == chatbot.id
            assert persisted_chatbot.is_active is False

            print(
                "PASS: Inactive chatbot remains "
                "persisted but protected."
            )

            # -----------------------------------------------------
            # Inactive users cannot perform chatbot operations.
            # -----------------------------------------------------
            user_b.is_active = False

            database_session.commit()
            database_session.refresh(user_b)

            try:
                service.create_chatbot(
                    user=user_b,
                    name="Blocked Assistant",
                )

            except InactiveChatbotOwnerError:
                pass

            else:
                raise AssertionError(
                    "Inactive user created a chatbot."
                )

            print(
                "PASS: Inactive chatbot owner "
                "was rejected."
            )

            print(
                "PASS: Chatbot service "
                "validation completed."
            )

        finally:
            database_session.close()

            Base.metadata.drop_all(
                bind=test_engine
            )

            test_engine.dispose()


if __name__ == "__main__":
    test_chatbot_service()
