from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
import pytest
from app.main import app

client = TestClient(app)

def test_get_project_kpis_unauthorized():
    """Verifica que si no hay una cookie de sesión válida se retorne 401."""
    # Hacemos petición sin cookies
    response = client.get("/api/projects/PROJ-1/kpis")
    assert response.status_code == 401
    assert response.json()["detail"] == "No autenticado"


@patch('app.api.v1.endpoints.projects.get_current_user_id')
@patch('app.api.v1.endpoints.projects.check_user_exists')
@patch('app.api.v1.endpoints.projects.kpi_repo')
def test_get_project_kpis_success(mock_kpi_repo, mock_check_user, mock_current_user):
    """Verifica la obtención exitosa de KPIs para un usuario autenticado."""
    # 1. Configurar mocks de autenticación y usuario
    mock_current_user.return_value = 123
    mock_check_user.return_value = MagicMock()
    
    # 2. Configurar mock del repositorio de KPIs
    mock_query = MagicMock()
    mock_kpi_repo.get_all_by_project.return_value = mock_query
    
    # Simular registros devueltos por .all()
    mock_kpis = [
        MagicMock(
            id_proyecto="PROJ-1",
            id_sprint=None,
            velocity_total_sp=8.0,
            velocity_promedio_historico=8.0,
            throughput_issues=2,
            lead_time_promedio_dias=3.5,
            cycle_time_promedio_dias=2.5,
            fecha_calculo=MagicMock()
        )
    ]
    
    # Encadenamiento del query: query.order_by().offset().limit().all()
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    # Hacemos que devuelva objetos serializables (FastAPI los convertirá en JSON)
    mock_query.limit.return_value.all.return_value = [
        {
            "id_proyecto": "PROJ-1",
            "id_sprint": None,
            "velocity_total_sp": 8.0,
            "velocity_promedio_historico": 8.0,
            "throughput_issues": 2,
            "lead_time_promedio_dias": 3.5,
            "cycle_time_promedio_dias": 2.5
        }
    ]
    
    # Enviar cookie para que pase la validación inicial de FastAPI del middleware,
    # aunque get_current_user_id esté mockeado
    response = client.get(
        "/api/projects/PROJ-1/kpis",
        cookies={"session_id": "123.mockedsession"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id_proyecto"] == "PROJ-1"
    assert data[0]["velocity_total_sp"] == 8.0
    assert data[0]["lead_time_promedio_dias"] == 3.5
    assert data[0]["cycle_time_promedio_dias"] == 2.5


@patch('app.api.v1.endpoints.projects.get_current_user_id')
@patch('app.api.v1.endpoints.projects.check_user_exists')
@patch('app.api.v1.endpoints.projects.mapping_repo')
@patch('app.api.v1.endpoints.projects.calculate_and_save_kpis')
def test_save_project_mappings_endpoint(
    mock_calc_kpis,
    mock_mapping_repo,
    mock_check_user,
    mock_current_user
):
    """Verifica que el guardado de mapeos persista en BD y dispare el cálculo de KPIs."""
    mock_current_user.return_value = 123
    mock_check_user.return_value = MagicMock()
    
    mappings_payload = [
        {"estado_jira": "En Progreso", "estado_base": "IN_PROGRESS"},
        {"estado_jira": "Doing", "estado_base": "IN_PROGRESS"}
    ]
    
    response = client.post(
        "/api/projects/PROJ-1/mappings",
        json=mappings_payload,
        cookies={"session_id": "123.mockedsession"}
    )
    
    assert response.status_code == 200
    assert response.json()["message"] == "Mapeo guardado y KPIs recalculados con éxito"
    
    # Verificar que se llamó a la base de datos para borrar el mapeo anterior
    mock_mapping_repo.delete_by_project.assert_called_once()
    
    # Verificar que se crearon los nuevos mapeos
    assert mock_mapping_repo.create.call_count == 2
    
    # Verificar que se ejecutó el recalculo de KPIs
    mock_calc_kpis.assert_called_once()


from datetime import datetime

@patch('app.api.v1.endpoints.jira.get_current_user_id')
@patch('app.api.v1.endpoints.jira.check_user_exists')
@patch('app.api.v1.endpoints.jira.log_repo')
def test_get_sync_logs_endpoint_success(mock_log_repo, mock_check_user, mock_current_user):
    """Verifica que el endpoint de logs de sincronización serialice correctamente la respuesta."""
    mock_current_user.return_value = 123
    mock_check_user.return_value = MagicMock()
    
    # Simular registros de log devueltos por el repositorio
    mock_log = MagicMock()
    mock_log.id_log = 1
    mock_log.fecha_ejecucion = datetime(2026, 7, 16, 12, 0, 0)
    mock_log.tipo_sincronizacion = "MANUAL"
    mock_log.resultado = "SUCCESS"
    mock_log.tiempo_ejecucion_segundos = 10
    mock_log.issues_procesados = 100
    mock_log.detalle_error = None
    mock_log.ejecutado_por = "USER_123"
    
    mock_log_repo.get_recent.return_value = [mock_log]
    
    response = client.get(
        "/api/jira/sync/logs",
        cookies={"session_id": "123.mockedsession"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id_log"] == 1
    assert data[0]["tipo_sincronizacion"] == "MANUAL"
    assert data[0]["resultado"] == "SUCCESS"
    assert data[0]["tiempo_ejecucion_segundos"] == 10
    assert data[0]["issues_procesados"] == 100
    assert data[0]["detalle_error"] is None

