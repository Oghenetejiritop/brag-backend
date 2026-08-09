
"""
Repository for persistent BRAG API-key records.

This module isolates API-key database operations from
authentication services and API route handlers.
"""

from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.api_key import APIKey


class APIKeyRepository:
    """
    Provides persistence operations for BRAG API keys.

    The repository receives an existing SQLAlchemy Session,
    keeping session lifecycle management outside this class.
    """

    def __init__(
        self,
        database_session: Session,
    ) -> None:
        """
        Initialize the API-key repository.

        Args:
            database_session:
                Active SQLAlchemy session used for database operations.
        """

        self._database_session = database_session

    def create_api_key(
        self,
        user_db_id: int,
        key_prefix: str,
        key_hash: str,
    ) -> APIKey:
        """
        Create and persist an API-key record.

        Args:
            user_id:
                Internal database ID of the key owner.

            key_prefix:
                Non-secret prefix used to identify the key.

            key_hash:
                Cryptographic hash of the complete API key.

        Returns:
            Newly persisted APIKey record.
        """

        api_key = APIKey(
            user_id=user_db_id,
            key_prefix=key_prefix,
            key_hash=key_hash,
        )

        self._database_session.add(api_key)

        try:
            # Commit so the API-key record receives its generated
            # database values before being returned.
            self._database_session.commit()

            self._database_session.refresh(api_key)

        except Exception:
            # Restore the session to a usable state when persistence
            # fails, such as from a duplicate key hash.
            self._database_session.rollback()
            raise

        return api_key

    def get_by_hash(
        self,
        key_hash: str,
    ) -> APIKey | None:
        """
        Retrieve an API-key record by its stored hash.

        Args:
            key_hash:
                Hash generated from the incoming API key.

        Returns:
            Matching APIKey or None if the hash does not exist.
        """

        statement = select(APIKey).where(
            APIKey.key_hash == key_hash
        )

        return self._database_session.scalar(
            statement
        )

    def get_by_id(
        self,
        api_key_id: int,
    ) -> APIKey | None:
        """
        Retrieve an API key using its internal primary key.
        """

        return self._database_session.get(
            APIKey,
            api_key_id,
        )

    def get_by_user_id(
        self,
        user_id: int,
    ) -> list[APIKey]:
        """
        Retrieve all API keys belonging to a user.

        Args:
            user_id:
                Internal database ID of the user.

        Returns:
            List of APIKey records owned by the user.
        """

        statement = (
            select(APIKey)
            .where(APIKey.user_id == user_id)
            .order_by(APIKey.created_at.desc())
        )

        return list(
            self._database_session.scalars(
                statement
            ).all()
        )

    def revoke(
        self,
        api_key: APIKey,
    ) -> APIKey:
        """
        Revoke an API key without deleting its database record.

        Args:
            api_key:
                APIKey record to disable.

        Returns:
            Updated APIKey record.
        """

        api_key.is_active = False

        try:
            self._database_session.commit()
            self._database_session.refresh(api_key)

        except Exception:
            self._database_session.rollback()
            raise

        return api_key

    def update_last_used(
        self,
        api_key: APIKey,
    ) -> APIKey:
        """
        Record when an API key successfully authenticated a request.

        Args:
            api_key:
                APIKey record that was successfully used.

        Returns:
            Updated APIKey record.
        """

        api_key.last_used_at = datetime.now(
            timezone.utc
        )

        try:
            self._database_session.commit()
            self._database_session.refresh(api_key)

        except Exception:
            self._database_session.rollback()
            raise

        return api_key
