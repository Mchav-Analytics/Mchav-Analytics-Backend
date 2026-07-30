"""Pruebas unitarias del cliente Jira (httpx mockeado)."""

from unittest.mock import MagicMock, patch

import pytest

from app.core.exceptions import JiraConnectionError, JiraQueryError
from app.datasources.jira_client import JiraClient


@pytest.fixture
def jira_client():
    client = JiraClient()
    client.base_url = "https://example.atlassian.net"
    client.email = "admin@example.com"
    client.api_token = "token"
    return client


def test_test_connection_ok(jira_client):
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"displayName": "Admin"}

    mock_http = MagicMock()
    mock_http.__enter__.return_value = mock_http
    mock_http.get.return_value = mock_response

    with patch.object(jira_client, "_http", return_value=mock_http):
        result = jira_client.test_connection()

    assert result["ok"] is True
    assert result["cuenta"] == "Admin"


def test_get_project_not_found(jira_client):
    mock_response = MagicMock()
    mock_response.status_code = 404

    mock_http = MagicMock()
    mock_http.__enter__.return_value = mock_http
    mock_http.get.return_value = mock_response

    with patch.object(jira_client, "_http", return_value=mock_http):
        assert jira_client.get_project("NOPE") is None


def test_search_issues_invalid_jql(jira_client):
    mock_response = MagicMock()
    mock_response.status_code = 400
    mock_response.text = "bad jql"

    mock_http = MagicMock()
    mock_http.__enter__.return_value = mock_http
    mock_http.get.return_value = mock_response

    with patch.object(jira_client, "_http", return_value=mock_http):
        with pytest.raises(JiraQueryError):
            jira_client.search_issues("INVALID")


def test_not_configured_raises():
    client = JiraClient()
    client.base_url = ""
    with pytest.raises(JiraConnectionError):
        client.get_project("SCRUM")
