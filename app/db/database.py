"""
SQLAlchemy database configuration for BRAG.

This module centralizes database engine creation, session management,
and the declarative base used by future ORM models.
"""

from collections.abc import Generator

from sqlalchemy import (
    create_engine,
    event,
    )

from sqlalchemy.orm import (
    DeclarativeBase,
    Session,
    sessionmaker,
)

from app.core.config import DATABASE_URL


# SQLite restricts connections to the thread that created them by default.
# FastAPI may execute request work across different threads, so this setting
# allows the SQLAlchemy-managed connection to be used safely by the request.
SQLITE_CONNECT_ARGS = {
    "check_same_thread": False,
}


# The engine owns the database connection pool and is created once for the
# application rather than once per request.
engine = create_engine(
    DATABASE_URL,
    connect_args=SQLITE_CONNECT_ARGS if DATABASE_URL.startswith("sqlite:") else {},
)

# SQLite does not enforce foreign-key constraints by default.
# Enable them for every SQLAlchemy-managed database connection
# so API-key records cannot reference users that do not exist.
def enable_sqlite_foreign_keys(
    database_connection,
    connection_record,
) -> None:
    """
    Enable relational foreign-key enforcement for SQLite.

    The connection_record argument is required by SQLAlchemy's
    connection event interface but is not needed by this function.
    """

    del connection_record

    cursor = database_connection.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


if engine.dialect.name == "sqlite":
    event.listen(engine, "connect", enable_sqlite_foreign_keys)


# The session factory creates independent database sessions. Each request
# will receive its own Session instance through get_database_session().
SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    expire_on_commit=False,
)


class Base(DeclarativeBase):
    """
    Base class inherited by all BRAG SQLAlchemy ORM models.
    """


def get_database_session() -> Generator[Session, None, None]:
    """
    Provide one SQLAlchemy session for a request.

    Yields:
        An active SQLAlchemy Session.

    The finally block guarantees that the session is closed even when
    request processing raises an exception.
    """

    database_session = SessionLocal()

    try:
        yield database_session
    finally:
        database_session.close()

