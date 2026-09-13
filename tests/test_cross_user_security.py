
"""
Cross-user access security tests for BRAG.

These tests verify that authenticated users cannot impersonate
another user by supplying client-controlled identifiers through
legacy headers or query parameters.
"""

from collections.abc import Generator
from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import (
    Session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool

import app.api.routes as routes_module

from app.api.dependencies import get_database_session
from app.db.database import Base
from app.db.models.api_key import APIKey
from app.db.models.user import User
from app.main import app
from app.repositories.user_repository import UserRepository
from app.services.authentication_service import AuthenticationService


TEST_DATABASE_URL = "sqlite://"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={
        "check_same_thread": False,
    },
    poolclass=StaticPool,
)

TestSessionLocal = sessionmaker(
    bind=test_engine,
    autoflush=False,
    expire_on_commit=False,
)


def override_database_session(
) -> Generator[Session, None, None]:
    """
    Provide an isolated database session for HTTP security tests.
    """

    database_session = TestSessionLocal()

    try:
        yield database_session
    finally:
        database_session.close()


class FakeRAGService:
    """
    Minimal RAG service used to identify which user's service
    was selected by the protected query route.
    """

    def __init__(
        self,
        answer: str,
    ) -> None:
        self._answer = answer

    def answer_question(
        self,
        question: str,
    ) -> str:
        """
        Return a fixed answer identifying this service.
        """

        del question

        return self._answer


class FakeRAGManager:
    """
    Minimal user-aware RAG manager for access-control testing.
    """

    def __init__(
        self,
        services: dict[str, FakeRAGService],
    ) -> None:
        self._services = services

    def has_service(
        self,
        user_id: str,
    ) -> bool:
        """
        Determine whether the authenticated user has a service.
        """

        return user_id in self._services

    def get_service(
        self,
        user_id: str,
    ) -> FakeRAGService:
        """
        Return only the service belonging to the supplied user.
        """

        return self._services[user_id]


def test_cross_user_access_security() -> None:
    """
    Verify that client-supplied identifiers cannot override
    the identity derived from bearer authentication.
    """

    Base.metadata.create_all(
        bind=test_engine
    )

    app.dependency_overrides[
        get_database_session
    ] = override_database_session

    database_session = TestSessionLocal()

    try:
        user_repository = UserRepository(
            database_session=database_session
        )

        authentication_service = AuthenticationService(
            database_session=database_session
        )

        # ---------------------------------------------------------
        # Create two independent users.
        # ---------------------------------------------------------
        user_a = user_repository.create_user()
        user_b = user_repository.create_user()

        assert user_a.user_id != user_b.user_id

        # ---------------------------------------------------------
        # Generate separate credentials.
        #
        # The plaintext keys are intentionally never printed.
        # ---------------------------------------------------------
        key_a = authentication_service.create_api_key(
            user=user_a
        )

        key_b = authentication_service.create_api_key(
            user=user_b
        )

        fake_rag_manager = FakeRAGManager(
            services={
                user_a.user_id: FakeRAGService(
                    answer="ANSWER_FROM_USER_A"
                ),
                user_b.user_id: FakeRAGService(
                    answer="ANSWER_FROM_USER_B"
                ),
            }
        )

        client = TestClient(app)

        with patch.object(
            routes_module,
            "rag_manager",
            fake_rag_manager,
        ):

            # =====================================================
            # Attack 1:
            #
            # User A supplies User B's UUID through the old
            # X-User-ID mechanism.
            #
            # BRAG must ignore it and use the identity resolved
            # from Key A.
            # =====================================================

            response = client.post(
                "/query",
                headers={
                    "Authorization": (
                        f"Bearer {key_a.api_key}"
                    ),
                    "X-User-ID": user_b.user_id,
                },
                json={
                    "question": "Which user am I?"
                },
            )

            assert response.status_code == 200

            assert response.json() == {
                "answer": "ANSWER_FROM_USER_A"
            }

            print(
                "PASS: Legacy X-User-ID cannot "
                "override bearer identity."
            )

            # =====================================================
            # Attack 2:
            #
            # User A attempts to select User B through an
            # unrecognized user_id query parameter.
            #
            # The protected route has no client-controlled user
            # selector, so authentication must still resolve A.
            # =====================================================

            response = client.post(
                f"/query?user_id={user_b.user_id}",
                headers={
                    "Authorization": (
                        f"Bearer {key_a.api_key}"
                    )
                },
                json={
                    "question": "Which user am I?"
                },
            )

            assert response.status_code == 200

            assert response.json() == {
                "answer": "ANSWER_FROM_USER_A"
            }

            print(
                "PASS: Query-string user ID cannot "
                "override bearer identity."
            )

            # =====================================================
            # Control test:
            #
            # Key B must still resolve to User B's own service.
            # =====================================================

            response = client.post(
                "/query",
                headers={
                    "Authorization": (
                        f"Bearer {key_b.api_key}"
                    )
                },
                json={
                    "question": "Which user am I?"
                },
            )

            assert response.status_code == 200

            assert response.json() == {
                "answer": "ANSWER_FROM_USER_B"
            }

            print(
                "PASS: User B reaches only "
                "User B's RAG service."
            )

        print(
            "PASS: Cross-user access "
            "security validated."
        )

    finally:
        database_session.close()

        app.dependency_overrides.clear()

        Base.metadata.drop_all(
            bind=test_engine
        )

        test_engine.dispose()


if __name__ == "__main__":
    test_cross_user_access_security()
