
"""
Server-managed browser session creation, verification, and revocation.
"""

from __future__ import annotations

import hashlib
import secrets

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models.browser_session import BrowserSession
from app.db.models.user import User


SESSION_LIFETIME = timedelta(hours=12)


def utc_now() -> datetime:
    """Return the current UTC time."""
    return datetime.now(timezone.utc)


def hash_session_token(token: str) -> str:
    """Hash a session token without retaining its plaintext."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class CreatedBrowserSession:
    """Return a token once, together with its expiration."""

    token: str
    expires_at: datetime


class BrowserSessionService:
    """Manage persistent browser sessions."""

    def __init__(self, database_session: Session) -> None:
        self._database_session = database_session

    def create(self, user: User) -> CreatedBrowserSession:
        """Create a session for an active user."""
        if user.id is None or not user.is_active:
            raise ValueError("An active, persisted user is required.")

        token = secrets.token_urlsafe(48)
        expires_at = utc_now() + SESSION_LIFETIME

        session = BrowserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            expires_at=expires_at,
        )

        self._database_session.add(session)

        try:
            self._database_session.commit()
        except Exception:
            self._database_session.rollback()
            raise

        return CreatedBrowserSession(
            token=token,
            expires_at=expires_at,
        )

    def authenticate(self, token: str | None) -> User | None:
        """Resolve a valid, unexpired session to its active owner."""
        if not isinstance(token, str) or not token:
            return None

        if len(token) > 512:
            return None

        token_hash = hash_session_token(token)

        statement = (
            select(User)
            .join(
                BrowserSession,
                BrowserSession.user_id == User.id,
            )
            .where(
                BrowserSession.token_hash == token_hash,
                BrowserSession.revoked_at.is_(None),
                BrowserSession.expires_at > utc_now(),
                User.is_active.is_(True),
            )
        )

        return self._database_session.scalar(statement)

    def revoke(self, token: str | None) -> bool:
        """Revoke a session. Return False if already invalid."""
        if not isinstance(token, str) or not token:
            return False

        if len(token) > 512:
            return False

        statement = select(BrowserSession).where(
            BrowserSession.token_hash == hash_session_token(token),
            BrowserSession.revoked_at.is_(None),
        )

        session = self._database_session.scalar(statement)

        if session is None:
            return False

        session.revoked_at = utc_now()

        try:
            self._database_session.commit()
        except Exception:
            self._database_session.rollback()
            raise

        return True
