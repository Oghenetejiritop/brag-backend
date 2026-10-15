"""Focused upload validation tests; no database or OpenAI calls."""
import io
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import UploadFile

from app.exceptions.upload_exceptions import (
    EmptyFilenameError,
    FileTooLargeError,
    UnsupportedDocumentTypeError,
)
from app.services.upload_service import UploadService


@pytest.fixture
def service(tmp_path: Path) -> UploadService:
    upload_service = UploadService.__new__(UploadService)
    upload_service._workspace_service = SimpleNamespace(
        get_chatbot_upload_directory=lambda **kwargs: tmp_path
    )
    return upload_service


def uploaded_file(name: str, contents: bytes) -> UploadFile:
    return UploadFile(filename=name, file=io.BytesIO(contents))


@pytest.mark.asyncio
async def test_accepts_pdf(service: UploadService, tmp_path: Path) -> None:
    result = await service.save_chatbot_file(
        user_id="user-a", chatbot_id="bot-a",
        file=uploaded_file("example.pdf", b"%PDF-1.4\nTest"),
    )
    assert Path(result).parent == tmp_path
    assert Path(result).read_bytes() == b"%PDF-1.4\nTest"


@pytest.mark.asyncio
async def test_rejects_unsupported_extension(service: UploadService, tmp_path: Path) -> None:
    with pytest.raises(UnsupportedDocumentTypeError):
        await service.save_chatbot_file(
            user_id="user-a", chatbot_id="bot-a",
            file=uploaded_file("malware.exe", b"data"),
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_rejects_empty_filename(service: UploadService, tmp_path: Path) -> None:
    with pytest.raises(EmptyFilenameError):
        await service.save_chatbot_file(
            user_id="user-a", chatbot_id="bot-a",
            file=uploaded_file("", b"data"),
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_rejects_oversized_pdf_and_cleans_up(service: UploadService, tmp_path: Path) -> None:
    with pytest.raises(FileTooLargeError):
        await service.save_chatbot_file(
            user_id="user-a", chatbot_id="bot-a",
            file=uploaded_file("large.pdf", b"x" * (10 * 1024 * 1024 + 1)),
        )
    assert list(tmp_path.iterdir()) == []


@pytest.mark.asyncio
async def test_accepts_exact_size_limit(service: UploadService) -> None:
    result = await service.save_chatbot_file(
        user_id="user-a", chatbot_id="bot-a",
        file=uploaded_file("limit.pdf", b"x" * (10 * 1024 * 1024)),
    )
    assert Path(result).stat().st_size == 10 * 1024 * 1024


@pytest.mark.asyncio
async def test_strips_windows_directory_from_filename(service: UploadService, tmp_path: Path) -> None:
    result = await service.save_chatbot_file(
        user_id="user-a", chatbot_id="bot-a",
        file=uploaded_file(r"C:\Users\Test\example.pdf", b"%PDF"),
    )
    assert Path(result).parent == tmp_path
    assert Path(result).name.endswith("_example.pdf")
