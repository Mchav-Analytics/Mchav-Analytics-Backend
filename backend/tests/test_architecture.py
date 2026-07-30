"""Guarda de arquitectura limpia: reglas de dependencia entre capas."""

from __future__ import annotations

import ast
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1] / "app"


def _imports_of(relative: str) -> set[str]:
    path = APP_ROOT / relative
    tree = ast.parse(path.read_text(encoding="utf-8"))
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                found.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            found.add(node.module)
    return found


def test_oauth_auth_service_does_not_import_httpx():
    """El caso de uso OAuth no debe hacer HTTP; eso vive en datasources."""
    imports = _imports_of("services/oauth_auth_service.py")
    assert "httpx" not in imports
    assert not any(name.startswith("httpx") for name in imports)


def test_jira_controller_does_not_import_jira_client():
    """Controllers hablan con services, no con datasources."""
    imports = _imports_of("api/v1/controllers/jira_controller.py")
    assert "app.datasources.jira_client" not in imports
    assert "app.datasources" not in imports


def test_admin_controller_does_not_import_jira_client():
    imports = _imports_of("api/v1/controllers/admin_controller.py")
    assert "app.datasources.jira_client" not in imports


def test_kpi_service_does_not_query_sqlalchemy_directly():
    """KpiService debe usar KpiRepository, no db.query."""
    source = (APP_ROOT / "services/kpi_service.py").read_text(encoding="utf-8")
    assert "self.db.query" not in source
    assert "KpiRepository" in source


def test_sync_service_uses_jira_gateway_port():
    imports = _imports_of("services/sync_service.py")
    assert "app.ports.jira_gateway" in imports
