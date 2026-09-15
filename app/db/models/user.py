"""
Persistent user model for BRAG.

The User model represents the account that owns API keys,
documents, vector stores, chatbots, and future subscriptions.
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

    The integer primary key is used internally for efficient database
    relationships. The UUID-based user_id is safe to expose through
    application services and future public APIs.
    """

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    # Use a non-sequential public identifier so database row numbers
    # are never exposed as tenant identities.
    user_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    # Disabling a user later should immediately prevent authentication
    # without deleting their historical records.
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        server_default=true(),
    )

    # Let the database assign creation time so records created by
    # different application processes follow one consistent rule.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    # A user may own multiple API keys for separate integrations,
    # environments, or future key-rotation workflows.
    api_keys: Mapped[list[APIKey]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    # A user may own multiple independently addressable chatbots.
    # Ownership is enforced through the Chatbot.user_id foreign key.
    chatbots: Mapped[list["Chatbot"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """
        Return a safe developer representation without credentials.
        """

        return (
            f"User(id={self.id!r}, "
            f"user_id={self.user_id!r}, "
            f"is_active={self.is_active!r})"
        )

