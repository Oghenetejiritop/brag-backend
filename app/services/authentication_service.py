
"""
Authentication service for BRAG.

This service is responsible for generating API credentials,
hashing credentials before persistence, and authenticating
incoming API keys.
"""

import hashlib
import secrets

from sqlalchemy.orm import Session

from app.db.models.api_key import APIKey
from app.db.models.user import User

from app.exceptions.auth_exceptions import (
    InactiveAPIKeyError,
    InactiveUserError,
    InvalidAPIKeyError,
)

from app.models.api_key_result import APIKeyCreationResult

from app.repositories.api_key_repository import APIKeyRepository


class AuthenticationService:
    """
    Handles BRAG API-key creation and authentication.

    Plaintext API keys are never persisted. Only a deterministic
    cryptographic hash and a short non-secret prefix are stored.
    """

    API_KEY_PREFIX = "brag_live_"
    API_KEY_RANDOM_BYTES = 32
    DISPLAY_PREFIX_LENGTH = 16

    def __init__(
        self,
        database_session: Session,
    ) -> None:
        """
        Initialize the authentication service.

        Args:
            database_session:
                Active SQLAlchemy session for authentication-related
                persistence operations.
        """

        self._api_key_repository = APIKeyRepository(
            database_session=database_session
        )

    def create_api_key(
        self,
        user: User,
    ) -> APIKeyCreationResult:
        """
        Generate and persist a new API key for a user.

        Args:
            user:
                Persistent user who will own the API key.

        Returns:
            APIKeyCreationResult containing the plaintext credential.

        Raises:
            InactiveUserError:
                If the user has been disabled.
        """

        if not user.is_active:
            raise InactiveUserError(
                "Cannot create an API key for an inactive user."
            )

        plaintext_key = self._generate_api_key()

        key_hash = self._hash_api_key(
            plaintext_key
        )

        # Store only enough of the key to help users identify it
        # later without exposing the secret credential.
        key_prefix = plaintext_key[
            :self.DISPLAY_PREFIX_LENGTH
        ]

        api_key_record = (
            self._api_key_repository.create_api_key(
                user_db_id=user.id,
                key_prefix=key_prefix,
                key_hash=key_hash,
            )
        )

        return APIKeyCreationResult(
            api_key_id=api_key_record.id,
            key_prefix=api_key_record.key_prefix,
            api_key=plaintext_key,
        )

    def list_api_keys(
        self,
        user: User,
    ) -> list[APIKey]:
        """
        List API-key records belonging to an active user.

        The repository filters by the authenticated user's
        internal database ID.

        Secret key hashes must never be included in API responses.
        """
        if not user.is_active:
            raise InactiveUserError(
                "Cannot list keys for an inactive user."
            )

        return self._api_key_repository.get_by_user_id(
            user_id=user.id
        )

    def authenticate(
        self,
        plaintext_key: str,
    ) -> User:
        """
        Authenticate a plaintext API key.

        Args:
            plaintext_key:
                Credential supplied by the API client.

        Returns:
            User who owns the authenticated API key.

        Raises:
            InvalidAPIKeyError:
                If no matching API key exists.

            InactiveAPIKeyError:
                If the API key has been revoked.

            InactiveUserError:
                If the owning user is inactive.
        """

        if not plaintext_key:
            raise InvalidAPIKeyError(
                "API key is required."
            )

        key_hash = self._hash_api_key(
            plaintext_key
        )

        api_key = self._api_key_repository.get_by_hash(
            key_hash
        )

        if api_key is None:
            raise InvalidAPIKeyError(
                "Invalid API key."
            )

        if not api_key.is_active:
            raise InactiveAPIKeyError(
                "API key has been revoked."
            )

        user = api_key.user

        if not user.is_active:
            raise InactiveUserError(
                "API-key owner is inactive."
            )

        # Record successful use only after all authentication
        # checks have passed.
        self._api_key_repository.update_last_used(
            api_key
        )

        return user

    def _generate_api_key(self) -> str:
        """
        Generate a cryptographically secure BRAG API key.

        Returns:
            Newly generated plaintext API credential.
        """

        secret = secrets.token_urlsafe(
            self.API_KEY_RANDOM_BYTES
        )

        return f"{self.API_KEY_PREFIX}{secret}"

    @staticmethod
    def _hash_api_key(
        plaintext_key: str,
    ) -> str:
        """
        Produce a deterministic SHA-256 digest for API-key lookup.

        API keys are generated with high cryptographic entropy,
        unlike human-created passwords, so deterministic hashing
        allows secure database lookup without storing plaintext.

        Args:
            plaintext_key:
                Complete API key supplied at creation or authentication.

        Returns:
            Hexadecimal SHA-256 digest.
        """

        return hashlib.sha256(
            plaintext_key.encode("utf-8")
        ).hexdigest()
