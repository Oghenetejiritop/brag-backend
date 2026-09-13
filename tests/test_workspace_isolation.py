
"""
Workspace isolation tests for BRAG.

These tests verify that separate users receive independent
filesystem locations for uploaded documents and vector stores.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.workspace_service import WorkspaceService


def test_user_workspace_isolation() -> None:
    """
    Verify that two users receive independent BRAG workspaces.

    A temporary storage root is used so this test does not create
    or modify directories inside the application's real storage
    location.
    """

    user_a_id = "11111111-1111-1111-1111-111111111111"
    user_b_id = "22222222-2222-2222-2222-222222222222"

    with TemporaryDirectory() as temporary_directory:
        workspace_service = WorkspaceService(
            storage_directory=temporary_directory
        )

        # ---------------------------------------------------------
        # Resolve each user's root workspace.
        # ---------------------------------------------------------
        user_a_workspace = (
            workspace_service.get_user_workspace(
                user_id=user_a_id
            )
        )

        user_b_workspace = (
            workspace_service.get_user_workspace(
                user_id=user_b_id
            )
        )

        # ---------------------------------------------------------
        # Each user must receive a different root directory.
        # ---------------------------------------------------------
        assert user_a_workspace != user_b_workspace

        assert user_a_workspace.name == user_a_id
        assert user_b_workspace.name == user_b_id

        # ---------------------------------------------------------
        # Both workspaces must exist physically.
        # ---------------------------------------------------------
        assert user_a_workspace.exists()
        assert user_a_workspace.is_dir()

        assert user_b_workspace.exists()
        assert user_b_workspace.is_dir()

        # ---------------------------------------------------------
        # Resolve upload directories.
        # ---------------------------------------------------------
        user_a_uploads = (
            workspace_service.get_upload_directory(
                user_id=user_a_id
            )
        )

        user_b_uploads = (
            workspace_service.get_upload_directory(
                user_id=user_b_id
            )
        )

        assert user_a_uploads != user_b_uploads

        assert (
            user_a_uploads
            == user_a_workspace / "uploads"
        )

        assert (
            user_b_uploads
            == user_b_workspace / "uploads"
        )

        # ---------------------------------------------------------
        # Resolve vector-store directories.
        # ---------------------------------------------------------
        user_a_vector_store = (
            workspace_service.get_vector_store_directory(
                user_id=user_a_id
            )
        )

        user_b_vector_store = (
            workspace_service.get_vector_store_directory(
                user_id=user_b_id
            )
        )

        assert user_a_vector_store != user_b_vector_store

        assert (
            user_a_vector_store
            == user_a_workspace / "vector_store"
        )

        assert (
            user_b_vector_store
            == user_b_workspace / "vector_store"
        )

        # ---------------------------------------------------------
        # All generated directories must remain inside the
        # temporary BRAG storage root.
        # ---------------------------------------------------------
        storage_root = Path(
            temporary_directory
        ).resolve()

        assert (
            user_a_workspace.resolve().parent
            == storage_root
        )

        assert (
            user_b_workspace.resolve().parent
            == storage_root
        )

        print(
            "PASS: User A workspace:",
            user_a_workspace,
        )

        print(
            "PASS: User B workspace:",
            user_b_workspace,
        )

        print(
            "PASS: Upload directories are isolated."
        )

        print(
            "PASS: Vector-store directories are isolated."
        )

        print(
            "PASS: Workspace isolation validated."
        )


if __name__ == "__main__":
    test_user_workspace_isolation()