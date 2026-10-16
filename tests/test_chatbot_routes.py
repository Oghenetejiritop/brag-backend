
"""HTTP-level registration and authentication regression checks for BRAG."""

from fastapi.testclient import TestClient
from app.main import app

EXPECTED_CHATBOT_ROUTES = {
    ("POST", "/api/v1/chatbots"),
    ("GET", "/api/v1/chatbots"),
    ("GET", "/api/v1/chatbots/{chatbot_id}"),
    ("PATCH", "/api/v1/chatbots/{chatbot_id}/deactivate"),
}


def test_chatbot_routes() -> None:
    # Some FastAPI releases retain included routers as _IncludedRouter
    # objects; app.routes is therefore not a reliable endpoint inventory.
    with TestClient(app) as client:
        health = client.get("/health")
        assert health.status_code == 200, health.text

        schema_response = client.get("/openapi.json")
        assert schema_response.status_code == 200, schema_response.text
        paths = schema_response.json()["paths"]
        registered = {
            (method.upper(), path)
            for path, operations in paths.items()
            for method in operations
            if method.lower() in {"get", "post", "patch", "put", "delete"}
        }
        required = EXPECTED_CHATBOT_ROUTES | {
            ("GET", "/health"),
            ("POST", "/upload"),
            ("POST", "/query"),
        }
        missing = required - registered
        assert not missing, f"Missing OpenAPI operations: {sorted(missing)}"
        print("PASS: Chatbot and legacy operations appear in OpenAPI.")

        for method, path in [
            ("POST", "/api/v1/chatbots"),
            ("GET", "/api/v1/chatbots"),
            ("GET", "/api/v1/chatbots/test-chatbot"),
            ("PATCH", "/api/v1/chatbots/test-chatbot/deactivate"),
        ]:
            response = client.request(
                method,
                path,
                json={"name": "Test Chatbot"} if method == "POST" else None,
            )
            assert response.status_code == 401, (
                f"{method} {path}: expected 401, got {response.status_code}: "
                f"{response.text}"
            )
            print(f"PASS: {method} {path} requires authentication.")

        assert client.get("/this-route-does-not-exist").status_code == 404
        print("PASS: Unknown routes return 404.")
