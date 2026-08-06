"""
BRAG SQLAlchemy ORM models.

Importing models here ensures their tables are registered in the
shared Base.metadata collection before Alembic autogeneration runs.
"""

from app.db.models.api_key import APIKey
from app.db.models.user import User


__all__ = [
    "APIKey",
    "User",
]