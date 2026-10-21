
"""Add private-by-default publishing to assistants."""

from alembic import op
import sqlalchemy as sa

revision = "c3e24020d001"
down_revision = "b8d34029c002"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("chatbots", sa.Column("is_published", sa.Boolean(), nullable=False, server_default=sa.false()))

def downgrade():
    op.drop_column("chatbots", "is_published")
