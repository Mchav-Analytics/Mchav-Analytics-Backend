# tests/test_fase8_alertas_y_solicitudes.py
# Pruebas unitarias y de integración para la Fase 8 (Alertas del Sistema y Solicitudes de Ayuda)

import pytest
from app.services.alerts_engine_service import (
    scan_and_generate_alerts,
    get_system_alerts,
    acknowledge_alert,
    create_help_request,
    get_help_requests,
    update_help_request_status
)

def test_scan_and_generate_alerts():
    """Verifica que el escáner de alertas devuelva la lista de alertas generadas."""
    alerts = scan_and_generate_alerts(None, "PROJ-01")
    assert isinstance(alerts, list)
    assert len(alerts) >= 0
    if alerts:
        first = alerts[0]
        assert "tipo_alerta" in first
        assert "severidad" in first
        assert "mensaje" in first

def test_acknowledge_alert():
    """Verifica la marcación de una alerta como atendida."""
    res = acknowledge_alert(None, 101)
    assert res["atendida"] is True
    assert res["alert_id"] == 101

def test_create_and_update_help_request():
    """Verifica la creación y actualización de estado de una solicitud de ayuda."""
    payload = {
        "id_proyecto": "PROJ-01",
        "solicitado_por_name": "Test Dev",
        "solicitado_por_email": "testdev@mchav.com",
        "rol_usuario": "DEVELOPER",
        "titulo": "Prueba de solicitud de ayuda",
        "descripcion": "Necesito apoyo con la conexión de base de datos",
        "key_issue": "MCHAV-999",
        "prioridad": "ALTA"
    }
    new_req = create_help_request(None, payload)
    assert new_req["id_solicitud"] is not None
    assert new_req["estado"] == "PENDIENTE"
    assert new_req["titulo"] == "Prueba de solicitud de ayuda"

    # Actualizar a EN_ATENCION
    updated = update_help_request_status(None, new_req["id_solicitud"], "EN_ATENCION", "Líder Técnico")
    assert updated["estado"] == "EN_ATENCION"

    # Obtener todas
    all_reqs = get_help_requests(None, "PROJ-01")
    assert any(r["id_solicitud"] == new_req["id_solicitud"] for r in all_reqs)
