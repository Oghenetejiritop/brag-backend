
"""
Tests for BRAG chatbot API route registration and authentication.

These tests run without Uvicorn, a live HTTP server,
or a real API key.
"""

from fastapi.testclient import TestClient

from app.main import app


EXPECTED_CHATBOT_ROUTES = {
    ("POST", "/api/v1/chatbots"),
    ("GET", "/api/v1/chatbots"),
    ("GET", "/api/v1/chatbots/{chatbot_id}"),
    ("PATCH", "/api/v1/chatbots/{chatbot_id}/deactivate"),
}


def test_chatbot_routes() -> None:
    """Verify registered routes and authentication protection."""

    # Inspect the application before making any HTTP requests.
    registered_routes = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", set())
    }

    print("\nREGISTERED FASTAPI ROUTES:")

    for method, path in sorted(registered_routes):
        print(f"{method} {path}")

    # Check each required chatbot route individually.
    missing_routes = EXPECTED_CHATBOT_ROUTES - registered_routes

    if missing_routes:
        print("\nMISSING CHATBOT ROUTES:")

        for method, path in sorted(missing_routes):
            print(f"{method} {path}")

        raise AssertionError(
            "Some chatbot endpoints are not registered. "
            "Check app.main and app.api.chatbot_routes."
        )

    print("\nPASS: All four chatbot routes registered.")

    client = TestClient(app)

    # Every chatbot endpoint must reject unauthenticated requests.
    requests = [
        ("POST", "/api/v1/chatbots"),
        ("GET", "/api/v1/chatbots"),
        ("GET", "/api/v1/chatbots/test-chatbot"),
        (
            "PATCH",
            "/api/v1/chatbots/test-chatbot/deactivate",
        ),
    ]

    for method, path in requests:
        response = client.request(
            method=method,
            url=path,
            json={"name": "Test Chatbot"}
            if method == "POST"
            else None,
        )

        assert response.status_code == 401, (
            f"{method} {path}: expected HTTP 401, "
            f"received HTTP {response.status_code}. "
            f"Response: {response.text}"
        )

        print(f"PASS: {method} {path} requires authentication.")

    # Verify legacy endpoints remain available.
    legacy_routes = {
        ("GET", "/health"),
        ("POST", "/upload"),
        ("POST", "/query"),
    }

    missing_legacy_routes = legacy_routes - registered_routes

    assert not missing_legacy_routes, (
        f"Missing legacy routes: {missing_legacy_routes}"
    )

    print("\nPASS: Legacy API routes remain registered.")
    print("PASS: Chatbot route tests completed.")


if __name__ == "__main__":
    test_chatbot_routes()
