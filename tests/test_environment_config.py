
"""Phase 6.4.1 deployment configuration tests."""

import pytest

from app.core import config


def test_development_needs_no_production_secrets(monkeypatch):
    monkeypatch.setenv("BRAG_ENV", "development")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    config.validate_environment()


def test_unknown_environment_rejected(monkeypatch):
    monkeypatch.setenv("BRAG_ENV", "staginggg")
    with pytest.raises(ValueError, match="BRAG_ENV"):
        config.validate_environment()


def test_production_requires_openai_key(monkeypatch):
    monkeypatch.setenv("BRAG_ENV", "production")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with pytest.raises(ValueError, match="OPENAI_API_KEY"):
        config.validate_environment()


def test_production_requires_explicit_origins(monkeypatch):
    monkeypatch.setenv("BRAG_ENV", "production")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.delenv("BRAG_CORS_ORIGINS", raising=False)
    with pytest.raises(ValueError, match="BRAG_CORS_ORIGINS"):
        config.validate_environment()


def test_production_rejects_http_origin(monkeypatch):
    monkeypatch.setenv("BRAG_ENV", "production")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setenv("BRAG_CORS_ORIGINS", "http://example.com")
    with pytest.raises(ValueError, match="HTTPS"):
        config.validate_environment()


def test_production_requires_database_url(monkeypatch):
    monkeypatch.setenv("BRAG_ENV", "production")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setenv("BRAG_CORS_ORIGINS", "https://example.com")
    monkeypatch.delenv("BRAG_DATABASE_URL", raising=False)
    with pytest.raises(ValueError, match="BRAG_DATABASE_URL"):
        config.validate_environment()


def test_production_rejects_sqlite(monkeypatch):
    monkeypatch.setenv("BRAG_ENV", "production")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setenv("BRAG_CORS_ORIGINS", "https://example.com")
    monkeypatch.setenv("BRAG_DATABASE_URL", "sqlite:///./brag.db")
    monkeypatch.setattr(config, "DATABASE_URL", "sqlite:///./brag.db")
    with pytest.raises(ValueError, match="non-SQLite"):
        config.validate_environment()


def test_production_accepts_valid_settings(monkeypatch):
    monkeypatch.setenv("BRAG_ENV", "production")
    monkeypatch.setenv("OPENAI_API_KEY", "test-placeholder")
    monkeypatch.setenv("BRAG_CORS_ORIGINS", "https://example.com")
    monkeypatch.setenv("BRAG_DATABASE_URL", "postgresql+psycopg://user:pass@localhost/db")
    monkeypatch.setattr(config, "DATABASE_URL", "postgresql+psycopg://user:pass@localhost/db")
    config.validate_environment()
