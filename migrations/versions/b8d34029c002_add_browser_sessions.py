
"""Add persistent browser sessions.

Revision ID: b8d34029c002
Revises: a7c23018b001
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8d34029c002"
down_revision: Union[str, None] = "a7c23018b001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "browser_sessions",
        sa.Column(
            "id",
            sa.Integer(),
            primary_key=True,
            autoincrement=True,
        ),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "token_hash",
            sa.String(length=64),
            nullable=False,
            unique=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=False,
        ),
        sa.Column(
            "revoked_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_browser_sessions_user_id",
        "browser_sessions",
        ["user_id"],
    )

    op.create_index(
        "ix_browser_sessions_expires_at",
        "browser_sessions",
        ["expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_browser_sessions_expires_at",
        table_name="browser_sessions",
    )
    op.drop_index(
        "ix_browser_sessions_user_id",
        table_name="browser_sessions",
    )
    op.drop_table("browser_sessions")
