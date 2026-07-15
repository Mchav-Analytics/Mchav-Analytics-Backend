import pytest
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


def test_login_returns_auth_url_envelope():
    response = client.get("/api/auth/login")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "success"
    assert "auth_url" in body["data"]
    assert body["data"]["auth_url"].startswith("https://")


def test_protected_endpoint_requires_auth():
    response = client.get("/api/projects")
    assert response.status_code == 403 or response.status_code == 401
