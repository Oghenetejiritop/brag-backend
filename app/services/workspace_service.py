
"""
Filesystem workspace management for BRAG users.

Each authenticated BRAG user receives an isolated workspace
containing uploaded documents and vector-store data.
"""

from pathlib import Path
from uuid import UUID


class WorkspaceService:
    """
    Manages isolated filesystem workspaces for BRAG users.

    User identifiers are validated as UUIDs before they are used
    in filesystem paths. This prevents client-controlled or
    malformed identifiers from escaping the storage root.
    """

    def __init__(
        self,
        storage_directory: str = "storage",
    ) -> None:
        """
        Initialize the workspace service.

        Args:
            storage_directory:
                Root directory containing all user workspaces.
        """

        self._storage_directory = Path(
            storage_directory
        )

        self._storage_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def get_user_workspace(
        self,
        user_id: str,
    ) -> Path:
        """
        Return the isolated workspace for a BRAG user.

        Args:
            user_id:
                Public UUID belonging to the authenticated user.

        Returns:
            Path to the user's workspace.

        Raises:
            ValueError:
                If the supplied user identifier is not a valid UUID
                or would resolve outside the configured storage root.
        """

        normalized_user_id = self._normalize_user_id(
            user_id
        )

        storage_root = (
            self._storage_directory.resolve()
        )

        workspace = (
            storage_root / normalized_user_id
        ).resolve()

        # ---------------------------------------------------------
        # Defense in depth:
        #
        # UUID validation already prevents traversal characters,
        # but the containment check protects this filesystem
        # boundary if identifier rules change in the future.
        # ---------------------------------------------------------
        if not workspace.is_relative_to(
            storage_root
        ):
            raise ValueError(
                "User workspace must remain inside "
                "the configured storage directory."
            )

        workspace.mkdir(
            parents=True,
            exist_ok=True,
        )

        return workspace

    def get_upload_directory(
        self,
        user_id: str,
    ) -> Path:
        """
        Return the authenticated user's upload directory.
        """

        uploads = (
            self.get_user_workspace(user_id)
            / "uploads"
        )

        uploads.mkdir(
            parents=True,
            exist_ok=True,
        )

        return uploads

    def get_vector_store_directory(
        self,
        user_id: str,
    ) -> Path:
        """
        Return the authenticated user's vector-store directory.
        """

        vector_store = (
            self.get_user_workspace(user_id)
            / "vector_store"
        )

        vector_store.mkdir(
            parents=True,
            exist_ok=True,
        )

        return vector_store

    @staticmethod
    def _normalize_user_id(
        user_id: str,
    ) -> str:
        """
        Validate and normalize a BRAG public user identifier.

        Args:
            user_id:
                User identifier to validate.

        Returns:
            Canonical UUID string.

        Raises:
            ValueError:
                If the identifier is empty or is not a valid UUID.
        """

        if not isinstance(user_id, str):
            raise ValueError(
                "User ID must be a valid UUID string."
            )

        candidate = user_id.strip()

        if not candidate:
            raise ValueError(
                "User ID must be a valid UUID string."
            )

        try:
            parsed_user_id = UUID(candidate)

        except ValueError:
            raise ValueError(
                "User ID must be a valid UUID string."
            ) from None

        return str(parsed_user_id)
