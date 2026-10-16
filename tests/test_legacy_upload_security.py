
"""Regression tests for the legacy upload path."""
import asyncio
from io import BytesIO
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

import pytest
from fastapi import HTTPException, UploadFile

from app.api import routes
from app.core.config import MAX_UPLOAD_SIZE_BYTES
from app.exceptions.upload_exceptions import FileTooLargeError
from app.services.upload_service import UploadService


class WorkspaceStub:
    def __init__(self, path: Path) -> None:
        self.path = path

    def get_upload_directory(self, user_id: str) -> Path:
        self.path.mkdir(parents=True, exist_ok=True)
        return self.path


def service_at(path: Path) -> UploadService:
    service = UploadService.__new__(UploadService)
    service._workspace_service = WorkspaceStub(path)
    return service


def upload(name: str, data: bytes) -> UploadFile:
    return UploadFile(filename=name, file=BytesIO(data))


def test_legacy_upload_accepts_pdf(tmp_path: Path) -> None:
    saved = asyncio.run(service_at(tmp_path).save_file("user", upload("ok.pdf", b"%PDF-1.4")))
    assert Path(saved).read_bytes() == b"%PDF-1.4"


def test_legacy_upload_strips_windows_directories(tmp_path: Path) -> None:
    saved = asyncio.run(service_at(tmp_path).save_file("user", upload(r"C:\temp\doc.pdf", b"abc")))
    assert Path(saved).parent == tmp_path
    assert Path(saved).name.endswith("_doc.pdf")


def test_legacy_upload_rejects_oversize_and_removes_partial_file(tmp_path: Path) -> None:
    with pytest.raises(FileTooLargeError):
        asyncio.run(service_at(tmp_path).save_file("user", upload("big.pdf", b"x" * (MAX_UPLOAD_SIZE_BYTES + 1))))
    assert list(tmp_path.iterdir()) == []


def test_legacy_upload_accepts_exact_limit(tmp_path: Path) -> None:
    saved = asyncio.run(service_at(tmp_path).save_file("user", upload("exact.pdf", b"x" * (MAX_UPLOAD_SIZE_BYTES))))
    assert Path(saved).stat().st_size == MAX_UPLOAD_SIZE_BYTES


def test_legacy_route_maps_size_error_to_413(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes.upload_service, "save_file", AsyncMock(side_effect=FileTooLargeError("secret")))
    with pytest.raises(HTTPException) as caught:
        asyncio.run(routes.upload_file(upload("x.pdf", b""), SimpleNamespace(user_id="u")))
    assert caught.value.status_code == 413
    assert "secret" not in caught.value.detail


def test_legacy_route_does_not_expose_unexpected_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(routes.upload_service, "save_file", AsyncMock(side_effect=RuntimeError("PRIVATE DATABASE PASSWORD")))
    with pytest.raises(RuntimeError, match="PRIVATE DATABASE PASSWORD"):
        asyncio.run(routes.upload_file(upload("x.pdf", b""), SimpleNamespace(user_id="u")))


def test_shared_limit_applies_to_both_upload_methods() -> None:
    import inspect
    from app.services.upload_service import UploadService
    assert inspect.getsource(UploadService.save_file).count("MAX_UPLOAD_SIZE_BYTES") >= 1
    assert inspect.getsource(UploadService.save_chatbot_file).count("MAX_UPLOAD_SIZE_BYTES") >= 1
