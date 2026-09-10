# tests/test_resiliencia_jira_tenacity.py
# Pruebas automatizadas para validar la Resiliencia de la API de Jira con Tenacity (Item 1)

import pytest
import httpx
from unittest.mock import AsyncMock, MagicMock, patch
from app.datasources.jira_datasource import JiraDatasource, JiraTransientError

@pytest.mark.anyio
async def test_jira_reintento_automatico_en_rate_limiting_429():
    """Verifica que Tenacity reintente automáticamente cuando Jira responde HTTP 429 Too Many Requests"""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    
    # 1era respuesta: 429 Too Many Requests, 2da respuesta: 200 OK
    res_429 = MagicMock(status_code=429, text="Rate limit exceeded")
    res_200 = MagicMock(status_code=200, json=lambda: [{"id": "1", "key": "PROJ-1", "name": "Proyecto 1"}])
    
    mock_client.get.side_effect = [res_429, res_200]
    
    projects = await JiraDatasource.fetch_projects(mock_client, "https://jira.example.com", {})
    
    assert len(projects) == 1
    assert projects[0]["key"] == "PROJ-1"
    assert mock_client.get.call_count == 2

@pytest.mark.anyio
async def test_jira_reintento_en_timeout_de_red():
    """Verifica que Tenacity reintente en caso de Timeout de red (httpx.TimeoutException)"""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    
    res_200 = MagicMock(status_code=200, json=lambda: {"total": 5, "issues": []})
    mock_client.get.side_effect = [httpx.TimeoutException("Connection timeout"), res_200]
    
    result = await JiraDatasource.fetch_issues_jql(mock_client, "https://jira.example.com", {}, "project = MCHAV")
    
    assert result["total"] == 5
    assert mock_client.get.call_count == 2
