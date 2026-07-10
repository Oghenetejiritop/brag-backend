from pathlib import Path


class WorkspaceService:
    """
    Manages per-user workspace directories.

    Responsibilities:
        - Create a workspace for each user.
        - Provide paths for uploads.
        - Provide paths for vector stores.

    This service centralizes filesystem layout so that other
    services remain independent of directory structure.
    """

    def __init__(
        self,
        storage_directory: str = "storage",
    ) -> None:
        """
        Initialize the workspace service.

        Args:
            storage_directory:
                Root directory that stores all user workspaces.
        """

        self._storage_directory = Path(storage_directory)

        # -------------------------------------------------------------
        # Ensure the root storage directory exists.
        # -------------------------------------------------------------
        self._storage_directory.mkdir(
            parents=True,
            exist_ok=True,
        )

    def get_user_workspace(
        self,
        user_id: str,
    ) -> Path:
        """
        Return the root workspace directory for a user.

        The directory is created automatically if it does not
        already exist.

        Args:
            user_id:
                Temporary user identifier.

        Returns:
            Path to the user's workspace.
        """

        workspace = self._storage_directory / user_id

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
        Return the uploads directory for a user.

        Args:
            user_id:
                Temporary user identifier.

        Returns:
            Path to the user's uploads directory.
        """

        uploads = self.get_user_workspace(user_id) / "uploads"

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
        Return the vector store directory for a user.

        Args:
            user_id:
                Temporary user identifier.

        Returns:
            Path to the user's vector store directory.
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
