
"""CORS regression tests for the real BRAG FastAPI app."""
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import get_cors_origins


@pytest.fixture
def client():
    return TestClient(app)


def test_allowed_origin_preflight(client):
    response = client.options(
        "/api/v1/chatbots",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "authorization",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "authorization" in response.headers["access-control-allow-headers"].lower()


def test_rejected_origin_preflight(client):
    response = client.options(
        "/api/v1/chatbots",
        headers={
            "Origin": "https://untrusted.example",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 400
    assert response.headers.get("access-control-allow-origin") is None


def test_allowed_origin_does_not_bypass_authentication(client):
    response = client.get(
        "/api/v1/chatbots",
        headers={"Origin": "http://localhost:5173"},
    )
    assert response.status_code == 401
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_explicit_environment_origins(monkeypatch):
    monkeypatch.setenv("BRAG_CORS_ORIGINS", "https://brag.example, https://app.example")
    assert get_cors_origins() == ["https://brag.example", "https://app.example"]


def test_wildcard_rejected(monkeypatch):
    monkeypatch.setenv("BRAG_CORS_ORIGINS", "*")
    with pytest.raises(ValueError):
        get_cors_origins()
