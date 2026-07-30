"""Pruebas de API (TestClient de FastAPI)."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert "status" in body
    assert "database" in body


def test_openapi_docs_available():
    response = client.get("/openapi.json")
    assert response.status_code == 200
    schema = response.json()
    assert schema["info"]["title"] == "MCHAV Analytics Backend"
    assert schema["info"]["version"] == "1.2.0"


def test_swagger_ui_available():
    response = client.get("/docs")
    assert response.status_code == 200


def test_login_returns_auth_url_envelope():
    response = client.get("/api/auth/oauth/login")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "auth_url" in body["data"]
    assert body["data"]["auth_url"].startswith("https://")


def test_legacy_login_still_works():
    response = client.get("/api/auth/login")
    assert response.status_code == 200
    assert "auth_url" in response.json()["data"]


def test_protected_endpoint_requires_auth():
    response = client.get("/api/projects")
    assert response.status_code in {401, 403}


def test_api_routes_registered_in_openapi():
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/auth/oauth/login" in paths
    assert "/api/auth/local/login" in paths
    assert "/api/projects" in paths
    assert "/api/kpis/sprints/{sprint_id}" in paths
    assert "/health" in paths
