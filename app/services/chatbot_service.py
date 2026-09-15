
"""
Business logic for persistent BRAG chatbots.

The service coordinates chatbot domain rules while delegating
database persistence to ChatbotRepository.
"""

from sqlalchemy.orm import Session

from app.db.models.chatbot import Chatbot
from app.db.models.user import User
from app.exceptions.chatbot_exceptions import (
    ChatbotNotFoundError,
    InactiveChatbotError,
    InactiveChatbotOwnerError,
    InvalidChatbotNameError,
)
from app.repositories.chatbot_repository import (
    ChatbotRepository,
)


class ChatbotService:
    """
    Manage persistent chatbots and enforce ownership rules.

    API routes should use this service rather than accessing
    ChatbotRepository directly.
    """

    MAX_NAME_LENGTH = 100
    MAX_DESCRIPTION_LENGTH = 500

    def __init__(
        self,
        database_session: Session,
    ) -> None:
        """
        Initialize the chatbot service.

        Args:
            database_session:
                Request-scoped SQLAlchemy database session.
        """

        self._chatbot_repository = ChatbotRepository(
            database_session=database_session
        )

    def create_chatbot(
        self,
        user: User,
        name: str,
        description: str | None = None,
    ) -> Chatbot:
        """
        Create a persistent chatbot for an active user.

        Args:
            user:
                Authenticated owner of the new chatbot.

            name:
                Human-readable chatbot name.

            description:
                Optional chatbot description.

        Returns:
            Newly persisted Chatbot.

        Raises:
            InactiveChatbotOwnerError:
                If the owning user is inactive.

            InvalidChatbotNameError:
                If the chatbot name is empty or exceeds the
                supported length.

            ValueError:
                If the description exceeds the supported length.
        """

        self._validate_active_user(
            user
        )

        normalized_name = self._normalize_name(
            name
        )

        normalized_description = (
            self._normalize_description(
                description
            )
        )

        return self._chatbot_repository.create(
            user_db_id=user.id,
            name=normalized_name,
            description=normalized_description,
        )

    def get_chatbot(
        self,
        user: User,
        public_chatbot_id: str,
        require_active: bool = True,
    ) -> Chatbot:
        """
        Retrieve a chatbot owned by the supplied user.

        Ownership is enforced inside the database query so a
        caller cannot retrieve another user's chatbot through
        this service.

        Args:
            user:
                Authenticated chatbot owner.

            public_chatbot_id:
                Public UUID of the requested chatbot.

            require_active:
                Whether inactive chatbots should be rejected.

        Returns:
            Matching user-owned Chatbot.

        Raises:
            InactiveChatbotOwnerError:
                If the authenticated user is inactive.

            ChatbotNotFoundError:
                If the chatbot does not exist or is not owned
                by the supplied user.

            InactiveChatbotError:
                If the chatbot is inactive and active state
                is required.
        """

        self._validate_active_user(
            user
        )

        chatbot = (
            self._chatbot_repository
            .get_by_chatbot_id_and_user_id(
                public_chatbot_id=public_chatbot_id,
                user_db_id=user.id,
            )
        )

        if chatbot is None:
            # Do not distinguish "does not exist" from "belongs
            # to another user." That avoids leaking tenant data.
            raise ChatbotNotFoundError(
                "Chatbot was not found."
            )

        if require_active and not chatbot.is_active:
            raise InactiveChatbotError(
                "Chatbot is inactive."
            )

        return chatbot

    def get_user_chatbots(
        self,
        user: User,
    ) -> list[Chatbot]:
        """
        Retrieve all chatbots owned by an active user.

        Args:
            user:
                Authenticated chatbot owner.

        Returns:
            Persistent chatbots owned by the user.

        Raises:
            InactiveChatbotOwnerError:
                If the authenticated user is inactive.
        """

        self._validate_active_user(
            user
        )

        return self._chatbot_repository.get_by_user_id(
            user_db_id=user.id
        )

    def deactivate_chatbot(
        self,
        user: User,
        public_chatbot_id: str,
    ) -> Chatbot:
        """
        Deactivate a chatbot owned by the supplied user.

        The chatbot remains persisted but can no longer be used
        for operations that require an active chatbot.

        Args:
            user:
                Authenticated chatbot owner.

            public_chatbot_id:
                Public UUID of the chatbot to deactivate.

        Returns:
            Deactivated Chatbot.

        Raises:
            InactiveChatbotOwnerError:
                If the authenticated user is inactive.

            ChatbotNotFoundError:
                If the chatbot does not exist or belongs to
                another user.

            InactiveChatbotError:
                If the chatbot is already inactive.
        """

        chatbot = self.get_chatbot(
            user=user,
            public_chatbot_id=public_chatbot_id,
        )

        return self._chatbot_repository.deactivate(
            chatbot
        )

    @classmethod
    def _normalize_name(
        cls,
        name: str,
    ) -> str:
        """
        Validate and normalize a chatbot name.

        Returns:
            Trimmed chatbot name.

        Raises:
            InvalidChatbotNameError:
                If the name is empty, not a string, or exceeds
                the supported length.
        """

        if not isinstance(name, str):
            raise InvalidChatbotNameError(
                "Chatbot name must be a string."
            )

        normalized_name = name.strip()

        if not normalized_name:
            raise InvalidChatbotNameError(
                "Chatbot name is required."
            )

        if (
            len(normalized_name)
            > cls.MAX_NAME_LENGTH
        ):
            raise InvalidChatbotNameError(
                "Chatbot name must not exceed "
                f"{cls.MAX_NAME_LENGTH} characters."
            )

        return normalized_name

    @classmethod
    def _normalize_description(
        cls,
        description: str | None,
    ) -> str | None:
        """
        Validate and normalize an optional description.

        Empty descriptions are stored as None.

        Raises:
            ValueError:
                If the description is not a string or exceeds
                the supported length.
        """

        if description is None:
            return None

        if not isinstance(description, str):
            raise ValueError(
                "Chatbot description must be a string."
            )

        normalized_description = (
            description.strip()
        )

        if not normalized_description:
            return None

        if (
            len(normalized_description)
            > cls.MAX_DESCRIPTION_LENGTH
        ):
            raise ValueError(
                "Chatbot description must not exceed "
                f"{cls.MAX_DESCRIPTION_LENGTH} characters."
            )

        return normalized_description

    @staticmethod
    def _validate_active_user(
        user: User,
    ) -> None:
        """
        Ensure chatbot operations are performed by an active user.

        Raises:
            InactiveChatbotOwnerError:
                If the user is inactive.
        """

        if not user.is_active:
            raise InactiveChatbotOwnerError(
                "Inactive users cannot perform "
                "chatbot operations."
            )
        