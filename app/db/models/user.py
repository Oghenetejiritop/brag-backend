
"""
Persistent user model for BRAG.

Users own API keys, chatbots, and future platform resources.

Email/password authentication is optional for existing accounts.
New browser accounts will use these fields after the registration
and login services are implemented.
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
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
    from app.db.models.api_key import APIKey
    from app.db.models.chatbot import Chatbot


class User(Base):
    """
    Represents a persistent BRAG user.

    The integer primary key is used internally for database
    relationships. The public UUID identifies the account
    through application services and public APIs.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    user_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    # Existing API-key-only accounts may have no email yet.
    # Registration will normalize emails before storing them.
    email: Mapped[str | None] = mapped_column(
        String(254),
        unique=True,
        index=True,
        nullable=True,
    )

    # Store only a password hash, never a plaintext password.
    # The password hashing service will be added separately.
    password_hash: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

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

    api_keys: Mapped[list[APIKey]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    chatbots: Mapped[list[Chatbot]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """
        Return a safe representation without credentials
        or personally identifying login information.
        """
        return (
            f"User(id={self.id!r}, "
            f"user_id={self.user_id!r}, "
            f"is_active={self.is_active!r})"
        )
