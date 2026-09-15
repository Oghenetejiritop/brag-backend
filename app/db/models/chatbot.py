
from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

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


class Chatbot(Base):
    """
    Represents a persistent BRAG chatbot owned by a user.

    A chatbot is an independently addressable RAG resource.
    Each chatbot belongs to exactly one user and receives a
    public UUID that can safely be exposed through the API.

    Database integer IDs remain internal implementation details.
    """

    __tablename__ = "chatbots"

    id: Mapped[int] = mapped_column(
        primary_key=True,
        autoincrement=True,
    )

    chatbot_id: Mapped[str] = mapped_column(
        String(36),
        unique=True,
        index=True,
        nullable=False,
        default=lambda: str(uuid4()),
    )

    user_id: Mapped[int] = mapped_column(
        ForeignKey(
            "users.id",
            ondelete="CASCADE",
        ),
        nullable=False,
        index=True,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    description: Mapped[str | None] = mapped_column(
        String(500),
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

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )

    user: Mapped["User"] = relationship(
        back_populates="chatbots",
    )

    def __repr__(self) -> str:
        """
        Return a developer-friendly representation of the chatbot.
        """

        return (
            f"Chatbot(id={self.id!r}, "
            f"chatbot_id={self.chatbot_id!r}, "
            f"user_id={self.user_id!r}, "
            f"name={self.name!r}, "
            f"is_active={self.is_active!r})"
        )
