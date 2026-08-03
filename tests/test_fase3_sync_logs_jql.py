import pytest
from unittest.mock import MagicMock
from fastapi import HTTPException
from app.api.v1.controllers.jql_controller import validate_jql_syntax
from app.repositories.metrics_repo import log_repo

def test_validador_sintaxis_jql_valida():
    """HU-009 CA-02: Aceptar consultas JQL bien formadas"""
    valid_jql = "project = 'MCHAV' AND statusCategory = 'In Progress' ORDER BY created DESC"
    assert validate_jql_syntax(valid_jql) is True

def test_validador_sintaxis_jql_parentesis_desbalanceados():
    """HU-009 CA-04: Rechazar consultas con paréntesis desbalanceados"""
    invalid_jql = "project = 'MCHAV' AND (status = 'Done'"
    with pytest.raises(HTTPException) as excinfo:
        validate_jql_syntax(invalid_jql)
    assert excinfo.value.status_code == 400
    assert "Paréntesis" in excinfo.value.detail

def test_validador_sintaxis_jql_comillas_abiertas():
    """HU-009 CA-04: Rechazar consultas con comillas sin cerrar"""
    invalid_jql = "project = 'MCHAV AND status = Done"
    with pytest.raises(HTTPException) as excinfo:
        validate_jql_syntax(invalid_jql)
    assert excinfo.value.status_code == 400
    assert "Comilla" in excinfo.value.detail

def test_validador_sintaxis_jql_sin_palabras_clave():
    """HU-009 CA-04: Rechazar consultas sin palabras clave reconocidas de JQL"""
    invalid_jql = "hello world 123"
    with pytest.raises(HTTPException) as excinfo:
        validate_jql_syntax(invalid_jql)
    assert excinfo.value.status_code == 400
    assert "no contiene un campo o filtro JQL reconocido" in excinfo.value.detail

def test_has_running_sync_metodo():
    """HU-007 CA-03: Verificar el método de detección de sincronización activa en el repositorio"""
    mock_db = MagicMock()
    mock_db.query().filter().count.return_value = 1
    
    assert log_repo.has_running_sync(mock_db) is True
