
"""
Filesystem security tests for BRAG user workspaces.

These tests verify that WorkspaceService accepts legitimate
public user UUIDs while rejecting identifiers that could escape
the configured storage root.
"""

from pathlib import Path
from tempfile import TemporaryDirectory

from app.services.workspace_service import WorkspaceService


def test_workspace_rejects_unsafe_user_ids() -> None:
    """
    Verify that unsafe identifiers cannot create paths outside
    the BRAG storage directory.
    """

    valid_user_id = (
        "11111111-1111-1111-1111-111111111111"
    )

    unsafe_user_ids = [
        "../outside",
        "../../outside",
        "user/../../outside",
        "/tmp/outside",
        "not-a-valid-user-id",
    ]

    with TemporaryDirectory() as temporary_directory:
        workspace_service = WorkspaceService(
            storage_directory=temporary_directory
        )

        storage_root = Path(
            temporary_directory
        ).resolve()

        # ---------------------------------------------------------
        # Control case:
        # A legitimate BRAG public UUID must still work normally.
        # ---------------------------------------------------------
        valid_workspace = (
            workspace_service.get_user_workspace(
                valid_user_id
            )
        )

        assert valid_workspace.exists()

        assert valid_workspace.resolve().parent == storage_root

        print(
            "PASS: Valid UUID remains inside "
            "the configured storage root."
        )

        # ---------------------------------------------------------
        # Attack cases:
        # Malformed/path-like identifiers must be rejected before
        # they can influence filesystem locations.
        # ---------------------------------------------------------
        for unsafe_user_id in unsafe_user_ids:
            try:
                workspace_service.get_user_workspace(
                    unsafe_user_id
                )

            except ValueError:
                pass

            else:
                raise AssertionError(
                    "Unsafe user identifier was accepted: "
                    f"{unsafe_user_id!r}"
                )

        print(
            "PASS: Unsafe workspace identifiers "
            "are rejected."
        )

        print(
            "PASS: Filesystem workspace safety validated."
        )


if __name__ == "__main__":
    test_workspace_rejects_unsafe_user_ids()
