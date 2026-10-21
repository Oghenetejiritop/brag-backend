
"""
Persistence operations for BRAG chatbots.

The repository isolates SQLAlchemy database operations from
application services and API routes.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.chatbot import Chatbot


class ChatbotRepository:
    """
    Provide persistent database operations for Chatbot records.

    This class is responsible only for persistence concerns.
    Authorization and business rules belong to higher-level
    application services.
    """

    def __init__(
        self,
        database_session: Session,
    ) -> None:
        """
        Initialize the repository with a database session.

        Args:
            database_session:
                SQLAlchemy session used for chatbot operations.
        """

        self._database_session = database_session

    def create(
        self,
        user_db_id: int,
        name: str,
        description: str | None = None,
    ) -> Chatbot:
        """
        Create and persist a chatbot for a user.

        Args:
            user_db_id:
                Internal database ID of the chatbot owner.

            name:
                Human-readable chatbot name.

            description:
                Optional chatbot description.

        Returns:
            Newly persisted Chatbot record.
        """

        chatbot = Chatbot(
            user_id=user_db_id,
            name=name,
            description=description,
        )

        self._database_session.add(
            chatbot
        )

        try:
            self._database_session.commit()
            self._database_session.refresh(
                chatbot
            )

        except Exception:
            # A failed transaction leaves the session unusable
            # until it has been rolled back.
            self._database_session.rollback()
            raise

        return chatbot

    def get_by_id(
        self,
        chatbot_id: int,
    ) -> Chatbot | None:
        """
        Retrieve a chatbot by its internal database ID.

        Args:
            chatbot_id:
                Internal Chatbot primary key.

        Returns:
            Matching Chatbot or None.
        """

        return self._database_session.get(
            Chatbot,
            chatbot_id,
        )

    def get_by_chatbot_id(
        self,
        public_chatbot_id: str,
    ) -> Chatbot | None:
        """
        Retrieve a chatbot by its public UUID.

        Args:
            public_chatbot_id:
                Public chatbot UUID exposed through BRAG APIs.

        Returns:
            Matching Chatbot or None.
        """

        statement = select(Chatbot).where(
            Chatbot.chatbot_id
            == public_chatbot_id
        )

        return self._database_session.scalar(
            statement
        )

    def get_by_user_id(
        self,
        user_db_id: int,
    ) -> list[Chatbot]:
        """
        Retrieve all chatbots owned by a user.

        Args:
            user_db_id:
                Internal database ID of the owner.

        Returns:
            Chatbots owned by the user, newest first.
        """

        statement = (
            select(Chatbot)
            .where(
                Chatbot.user_id == user_db_id
            )
            .order_by(
                Chatbot.created_at.desc()
            )
        )

        return list(
            self._database_session.scalars(
                statement
            ).all()
        )

    def get_by_chatbot_id_and_user_id(
        self,
        public_chatbot_id: str,
        user_db_id: int,
    ) -> Chatbot | None:
        """
        Retrieve a chatbot only when it belongs to a user.

        This ownership-scoped query will support tenant isolation
        in the service and API layers.

        Args:
            public_chatbot_id:
                Public UUID of the requested chatbot.

            user_db_id:
                Internal database ID of the expected owner.

        Returns:
            Matching Chatbot when ownership matches, otherwise None.
        """

        statement = select(Chatbot).where(
            Chatbot.chatbot_id
            == public_chatbot_id,
            Chatbot.user_id
            == user_db_id,
        )

        return self._database_session.scalar(
            statement
        )

    def deactivate(
        self,
        chatbot: Chatbot,
    ) -> Chatbot:
        """
        Mark a chatbot as inactive without deleting it.

        Args:
            chatbot:
                Persistent chatbot record to deactivate.

        Returns:
            Updated Chatbot record.
        """

        chatbot.is_active = False

        try:
            self._database_session.commit()
            self._database_session.refresh(
                chatbot
            )

        except Exception:
            # Restore the session after a failed transaction so it
            # remains usable by the application.
            self._database_session.rollback()
            raise

        return chatbot

    def set_published(self, chatbot: Chatbot, published: bool) -> Chatbot:
        chatbot.is_published = published
        try:
            self._database_session.commit()
            self._database_session.refresh(chatbot)
        except Exception:
            self._database_session.rollback()
            raise
        return chatbot

    def get_published(self, public_chatbot_id: str) -> Chatbot | None:
        statement = select(Chatbot).where(
            Chatbot.chatbot_id == public_chatbot_id,
            Chatbot.is_active.is_(True),
            Chatbot.is_published.is_(True),
        )
        return self._database_session.scalar(statement)
