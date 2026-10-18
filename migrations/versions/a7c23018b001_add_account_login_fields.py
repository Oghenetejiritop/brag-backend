
"""
Add account login fields to users.

Revision ID: a7c23018b001
Revises: f49f87210886

Existing users retain their IDs, API keys, and chatbots.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a7c23018b001"

down_revision: Union[str, None] = "f49f87210886"

branch_labels: Union[str, Sequence[str], None] = None

depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add optional account login fields."""

    op.add_column(
        "users",
        sa.Column(
            "email",
            sa.String(length=254),
            nullable=True,
        ),
    )

    op.add_column(
        "users",
        sa.Column(
            "password_hash",
            sa.String(length=255),
            nullable=True,
        ),
    )

    op.create_index(
        "ix_users_email",
        "users",
        ["email"],
        unique=True,
    )


def downgrade() -> None:
    """Remove account login fields."""

    op.drop_index(
        "ix_users_email",
        table_name="users",
    )

    op.drop_column(
        "users",
        "password_hash",
    )

    op.drop_column(
        "users",
        "email",
    )
