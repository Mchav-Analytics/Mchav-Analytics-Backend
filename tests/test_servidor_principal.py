import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app, startup_event

client = TestClient(app)

def test_obtener_mensaje_bienvenida_raiz():
    """Verifica que la ruta raíz '/' devuelva el mensaje de bienvenida."""
    response = client.get("/")
    assert response.status_code == 200
    assert "Bienvenido a la API de MCHAV Analytics" in response.json()["message"]

@patch('app.main.engine.connect')
@patch('app.main.SessionLocal')
def test_ejecutar_evento_inicio_servidor(mock_session_cls, mock_connect):
    """Verifica que el evento de startup ejecute las migraciones de columnas y la limpieza de logs."""
    mock_conn = MagicMock()
    mock_connect.return_value.__enter__.return_value = mock_conn
    
    mock_db = MagicMock()
    mock_session_cls.return_value = mock_db
    mock_db.query().filter().all.return_value = []
    
    startup_event()
    
    assert mock_conn.execute.call_count >= 3
    mock_db.close.assert_called_once()
