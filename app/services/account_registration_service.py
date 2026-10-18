
"""
BRAG account registration and password verification.

This service is separate from developer API-key authentication.
Existing API-key-only users remain supported.
"""

from __future__ import annotations

import re

from argon2 import PasswordHasher
from argon2.exceptions import (
    InvalidHashError,
    VerificationError,
    VerifyMismatchError,
)
from argon2.low_level import Type

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db.models.user import User


class RegistrationError(ValueError):
    """Invalid account registration input."""


class DuplicateEmailError(RegistrationError):
    """An account already uses the supplied email address."""


class AccountRegistrationService:
    """Create and verify BRAG email/password accounts."""

    def __init__(self, database_session: Session) -> None:
        self._database_session = database_session
        self._password_hasher = PasswordHasher(
            time_cost=3,
            memory_cost=65536,
            parallelism=4,
            hash_len=32,
            salt_len=16,
            type=Type.ID,
        )

    @staticmethod
    def normalize_email(email: str) -> str:
        """
        Normalize an email address for account lookup.

        BRAG's MVP uses lowercase email identifiers.
        This is an application policy, not a claim that all
        email providers treat addresses case-insensitively.
        """
        if not isinstance(email, str):
            raise RegistrationError("A valid email is required.")

        normalized = email.strip().lower()

        if (
            len(normalized) > 254
            or not re.fullmatch(
                r"[^@\s]+@[^@\s]+\.[^@\s]+",
                normalized,
            )
        ):
            raise RegistrationError("A valid email is required.")

        return normalized

    @staticmethod
    def validate_password(password: str) -> None:
        """
        Require a reasonably long password.

        Do not silently trim or modify passwords.
        """
        if not isinstance(password, str):
            raise RegistrationError("A valid password is required.")

        if len(password) < 12:
            raise RegistrationError(
                "Password must contain at least 12 characters."
            )

        if len(password.encode("utf-8")) > 1024:
            raise RegistrationError("Password is too long.")

        if "\x00" in password:
            raise RegistrationError(
                "Password contains an invalid character."
            )

    def register(self, email: str, password: str) -> User:
        """Create a new account with a hashed password."""
        normalized_email = self.normalize_email(email)
        self.validate_password(password)

        existing_user = self._database_session.scalar(
            select(User).where(User.email == normalized_email)
        )

        if existing_user is not None:
            raise DuplicateEmailError(
                "An account already uses this email address."
            )

        password_hash = self._password_hasher.hash(password)

        user = User(
            email=normalized_email,
            password_hash=password_hash,
        )

        self._database_session.add(user)

        try:
            self._database_session.commit()
            self._database_session.refresh(user)
        except IntegrityError as exc:
            self._database_session.rollback()
            raise DuplicateEmailError(
                "An account already uses this email address."
            ) from exc
        except Exception:
            self._database_session.rollback()
            raise

        return user

    def verify_credentials(
        self,
        email: str,
        password: str,
    ) -> User | None:
        """
        Verify account credentials.

        Return None for incorrect credentials or inactive users.
        This method does not create a browser session.
        """
        try:
            normalized_email = self.normalize_email(email)
        except RegistrationError:
            return None

        if not isinstance(password, str):
            return None

        user = self._database_session.scalar(
            select(User).where(User.email == normalized_email)
        )

        if (
            user is None
            or not user.is_active
            or not user.password_hash
        ):
            return None

        try:
            verified = self._password_hasher.verify(
                user.password_hash,
                password,
            )
        except (
            VerifyMismatchError,
            VerificationError,
            InvalidHashError,
        ):
            return None

        return user if verified else None
