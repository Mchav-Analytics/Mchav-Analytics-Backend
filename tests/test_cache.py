from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from app.core.cache import ShortLivedCache
from app.main import app

client = TestClient(app)

def test_short_lived_cache_basic_operations():
    """Prueba que ShortLivedCache realice correctamente get, set y clear."""
    cache = ShortLivedCache(ttl_seconds=10)
    cache.set("foo", "bar")
    assert cache.get("foo") == "bar"
    
    cache.clear()
    assert cache.get("foo") is None


def test_short_lived_cache_expiration():
    """Prueba que el valor de ShortLivedCache expire una vez pasado el TTL."""
    cache = ShortLivedCache(ttl_seconds=5)
    cache.set("hello", "world")
    assert cache.get("hello") == "world"
    
    # Simular paso del tiempo usando patch sobre datetime.now en el módulo de caché
    future = datetime.now() + timedelta(seconds=6)
    with patch('app.core.cache.datetime') as mock_datetime:
        mock_datetime.now.return_value = future
        # Debería retornar None debido a que ya expiró el TTL de 5s
        assert cache.get("hello") is None


@pytest.mark.anyio
@patch('app.api.v1.endpoints.jira.get_current_user_id')
@patch('app.api.v1.endpoints.jira.check_user_exists')
@patch('httpx.AsyncClient.get')
async def test_get_jira_metrics_uses_cache(mock_httpx_get, mock_check_user, mock_current_user):
    """Verifica que el endpoint /metrics use ShortLivedCache en llamadas repetidas."""
    from app.api.v1.endpoints.jira import metrics_cache
    metrics_cache.clear() # Limpiar cualquier residuo de pruebas
    
    mock_current_user.return_value = 55
    mock_user = MagicMock()
    mock_user.id_usuario = 55
    mock_user.cloud_id = "cloud-abc"
    mock_user.access_token = "token-123"
    mock_check_user.return_value = mock_user
    
    # Respuestas simuladas para las 4 peticiones JQL
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"total": 5}
    mock_httpx_get.return_value = mock_response
    
    # 1. Primera petición: Debería llamar a HTTPX
    response1 = client.get("/api/jira/metrics", cookies={"session_id": "55.mock"})
    assert response1.status_code == 200
    assert response1.json()["completed_tickets"] == 5
    # Se debió llamar 4 veces (1 por cada consulta en paralelo)
    assert mock_httpx_get.call_count == 4
    
    # Reset del conteo de llamadas para ver la segunda petición
    mock_httpx_get.reset_mock()
    
    # 2. Segunda petición: Debería retornar de caché (no hacer llamadas HTTPX)
    response2 = client.get("/api/jira/metrics", cookies={"session_id": "55.mock"})
    assert response2.status_code == 200
    assert response2.json()["completed_tickets"] == 5
    # No se debió llamar a httpx.AsyncClient.get ya que los datos se recuperan de caché
    mock_httpx_get.assert_not_called()
