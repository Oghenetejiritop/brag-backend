"""Safe API documentation configuration checks."""

import pytest

from app.core.config import get_api_documentation_settings


@pytest.mark.parametrize("environment", ["development", "testing"])
def test_docs_enabled_for_local_environments(monkeypatch, environment):
    monkeypatch.setenv("BRAG_ENV", environment)
    assert get_api_documentation_settings() == {
        "docs_url": "/docs",
        "redoc_url": "/redoc",
        "openapi_url": "/openapi.json",
    }


def test_docs_disabled_in_production(monkeypatch):
    monkeypatch.setenv("BRAG_ENV", "production")
    assert get_api_documentation_settings() == {
        "docs_url": None,
        "redoc_url": None,
        "openapi_url": None,
    }


def test_invalid_environment_rejected(monkeypatch):
    monkeypatch.setenv("BRAG_ENV", "unknown")
    with pytest.raises(ValueError, match="BRAG_ENV"):
        get_api_documentation_settings()
