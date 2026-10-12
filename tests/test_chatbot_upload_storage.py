import asyncio
from pathlib import Path
from tempfile import TemporaryDirectory
from uuid import uuid4
from io import BytesIO

from fastapi import UploadFile

from app.services.upload_service import UploadService
from app.services.workspace_service import WorkspaceService


async def run_test() -> None:
    with TemporaryDirectory() as directory:
        user_id = str(uuid4())
        chatbot_a = str(uuid4())
        chatbot_b = str(uuid4())

        service = UploadService()
        service._workspace_service = WorkspaceService(
            storage_directory=directory
        )

        async def save(chatbot_id: str) -> Path:
            upload = UploadFile(
                filename="example.pdf",
                file=BytesIO(b"BRAG test document"),
            )

            path = await service.save_chatbot_file(
                user_id=user_id,
                chatbot_id=chatbot_id,
                file=upload,
            )

            return Path(path)

        path_a = await save(chatbot_a)
        path_b = await save(chatbot_b)

        assert path_a.exists()
        assert path_b.exists()
        assert path_a != path_b
        assert path_a.parent != path_b.parent
        assert path_a.read_bytes() == b"BRAG test document"
        assert path_b.read_bytes() == b"BRAG test document"

        print("PASS: Chatbot uploads stored separately.")


if __name__ == "__main__":
    asyncio.run(run_test())