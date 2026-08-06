"""
BRAG SQLAlchemy ORM models.

Models are imported here so Alembic can discover them through
the shared Base.metadata collection.
"""

from app.db.models.user import User


__all__ = [
    "User",
]