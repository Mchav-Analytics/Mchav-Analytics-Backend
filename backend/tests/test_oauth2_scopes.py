"""Pruebas de autorización OAuth2 password + catálogo de scopes."""

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app

client = TestClient(app)


def test_projects_requires_auth():
    response = client.get("/api/projects")
    assert response.status_code == 401


def test_openapi_declares_oauth2_password():
    schema = client.get("/openapi.json").json()
    schemes = schema["components"]["securitySchemes"]
    oauth = schemes.get("OAuth2PasswordBearer")
    assert oauth is not None
    assert oauth["type"] == "oauth2"
    assert "password" in oauth["flows"]
    assert oauth["flows"]["password"]["tokenUrl"] == "/api/auth/local/token"


def test_scopes_catalog_endpoint():
    response = client.get("/api/auth/scopes")
    assert response.status_code == 200
    body = response.json()
    assert "projects:read" in body["data"]["scopes"]
    assert "admin" in body["data"]["role_examples"]["Administrador"]
    assert "local" in body["data"]["login_methods"]


def test_oauth_and_local_routes_in_openapi():
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/auth/oauth/login" in paths
    assert "/api/auth/local/login" in paths
    assert "/api/auth/local/token" in paths
    assert "/api/auth/local/refresh" in paths


def test_jwt_factory_still_works_for_bearer_tests():
    token = create_access_token(subject="1", scopes=["me", "projects:read"])
    assert token.startswith("eyJ")
