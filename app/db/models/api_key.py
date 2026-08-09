
"""
Persistent API-key model for BRAG.

This model stores API-key metadata and a cryptographic hash.
The complete plaintext API key must never be stored in the database.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    String,
    func,
    true,
)
from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.database import Base


if TYPE_CHECKING:
    from app.db.models.user import User


class APIKey(Base):
    """
    Represents an API key belonging to a BRAG user.

    Only the key hash and a safe, non-secret prefix are persisted.
    The complete API key will be returned only when it is created.
    """

    __tablename__ = "api_keys"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # Use the user's internal database ID for an efficient relational
    # link. The public UUID remains available through the User model.
    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    # A short prefix helps identify a key in dashboards and logs
    # without revealing the secret portion of the credential.
    key_prefix: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        index=True,
    )

    # The complete plaintext key is never stored. A 64-character
    # column is sufficient for a SHA-256 hexadecimal digest, which
    # we will implement in the authentication service later.
    key_hash: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        unique=True,
        index=True,
    )

    # Revocation disables a key without deleting its audit history.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # This remains null until the key successfully authenticates
    # a request for the first time.
    last_used_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Provides object-oriented access from an APIKey record to
    # the user who owns it.
    user: Mapped[User] = relationship(
        back_populates="api_keys",
    )

    def __repr__(self) -> str:
        """
        Return a safe representation that never exposes key material.
        """

        return (
            f"APIKey(id={self.id!r}, "
            f"user_id={self.user_id!r}, "
            f"key_prefix={self.key_prefix!r}, "
            f"is_active={self.is_active!r})"
        )

