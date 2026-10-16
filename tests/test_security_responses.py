
"""Focused tests of security response behavior without external services."""

from fastapi import FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.api.security import SecurityHeadersMiddleware, register_unexpected_error_handler


def make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(SecurityHeadersMiddleware)
    register_unexpected_error_handler(app)

    @app.get("/ok")
    def ok() -> dict[str, bool]:
        return {"ok": True}

    @app.get("/bad-request")
    def bad_request() -> None:
        raise HTTPException(status_code=400, detail="Invalid input")

    @app.get("/crash")
    def crash() -> None:
        raise RuntimeError("PRIVATE DATABASE PASSWORD SHOULD NOT APPEAR")

    return app


def test_security_headers_on_success() -> None:
    with TestClient(make_app()) as client:
        response = client.get("/ok")
    assert response.status_code == 200
    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["x-frame-options"] == "DENY"
    assert response.headers["referrer-policy"] == "no-referrer"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-security-policy"] == "frame-ancestors 'none'"


def test_security_headers_on_handled_error() -> None:
    with TestClient(make_app()) as client:
        response = client.get("/bad-request")
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid input"}
    assert response.headers["x-content-type-options"] == "nosniff"


def test_unexpected_error_is_sanitized() -> None:
    with TestClient(make_app(), raise_server_exceptions=False) as client:
        response = client.get("/crash")
    assert response.status_code == 500
    assert response.json() == {"detail": "An internal server error occurred."}
    assert "PRIVATE DATABASE PASSWORD" not in response.text
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_unexpected_error_does_not_change_http_errors() -> None:
    with TestClient(make_app(), raise_server_exceptions=False) as client:
        response = client.get("/bad-request")
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid input"
