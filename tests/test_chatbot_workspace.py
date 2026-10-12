
"""
Filesystem isolation tests for BRAG chatbot workspaces.

The tests use temporary storage and do not modify the
application's production storage directory.
"""

from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4

from app.services.workspace_service import WorkspaceService


def test_chatbot_workspace() -> None:
    """
    Verify chatbot-specific filesystem isolation and UUID safety.
    """
    with TemporaryDirectory() as temporary_directory:
        workspace_service = WorkspaceService(
            storage_directory=temporary_directory
        )

        user_a = str(uuid4())
        user_b = str(uuid4())

        chatbot_a = str(uuid4())
        chatbot_b = str(uuid4())

        # Two chatbots owned by the same user must have
        # separate persistent storage locations.
        workspace_a = workspace_service.get_chatbot_workspace(
            user_id=user_a,
            chatbot_id=chatbot_a,
        )

        workspace_b = workspace_service.get_chatbot_workspace(
            user_id=user_a,
            chatbot_id=chatbot_b,
        )

        assert workspace_a != workspace_b
        assert workspace_a.is_dir()
        assert workspace_b.is_dir()

        print("PASS: Chatbot workspaces are isolated.")

        # Different users must not share a workspace,
        # even if the same chatbot UUID is supplied.
        other_user_workspace = (
            workspace_service.get_chatbot_workspace(
                user_id=user_b,
                chatbot_id=chatbot_a,
            )
        )

        assert other_user_workspace != workspace_a

        print("PASS: User workspace boundaries are isolated.")

        # Each chatbot receives its own upload and vector
        # store directories.
        upload_directory = (
            workspace_service.get_chatbot_upload_directory(
                user_id=user_a,
                chatbot_id=chatbot_a,
            )
        )

        vector_directory = (
            workspace_service.get_chatbot_vector_store_directory(
                user_id=user_a,
                chatbot_id=chatbot_a,
            )
        )

        assert upload_directory.is_dir()
        assert vector_directory.is_dir()

        assert upload_directory.parent == workspace_a
        assert vector_directory.parent == workspace_a

        print("PASS: Chatbot storage directories were created.")

        # Malformed chatbot identifiers must not be accepted
        # as filesystem path components.
        try:
            workspace_service.get_chatbot_workspace(
                user_id=user_a,
                chatbot_id="../../outside",
            )
        except ValueError:
            pass
        else:
            raise AssertionError(
                "Invalid chatbot UUID was accepted."
            )

        print("PASS: Invalid chatbot UUID was rejected.")

        # Existing user-level workspace behavior must
        # remain available for earlier API routes.
        legacy_upload_directory = (
            workspace_service.get_upload_directory(user_a)
        )

        assert legacy_upload_directory.is_dir()
        assert legacy_upload_directory == (
            Path(temporary_directory).resolve()
            / user_a
            / "uploads"
        )

        print("PASS: Existing user workspace behavior preserved.")

        print("PASS: Chatbot workspace validation completed.")


if __name__ == "__main__":
    test_chatbot_workspace()
