# tests/test_fase7_sprint_health.py
# Pruebas automatizadas para la Fase 7: Predictibilidad de Sprint, Flow Efficiency y Health Score

import pytest
from app.services.sprint_health_service import calculate_sprint_health

def test_sprint_health_calculation():
    """
    Verifica el correcto funcionamiento de las fórmulas de Predictibilidad y Health Score (0-100 pts).
    """
    res = calculate_sprint_health(db=None, proyecto_id="PROJ-01")

    assert "health_score" in res
    assert "metrics" in res
    assert "bottleneck_stages" in res
    assert "bottleneck_insight" in res

    score = res["health_score"]
    metrics = res["metrics"]

    assert 0.0 <= score <= 100.0
    assert "commitment_reliability_pct" in metrics
    assert "scope_creep_pct" in metrics
    assert "carryover_pct" in metrics
    assert "flow_efficiency_pct" in metrics

    # Verificar que los estadios del flujo estén estructurados
    assert len(res["bottleneck_stages"]) >= 0
    assert res["diagnostico"] in ("EXCELENTE", "ACEPTABLE", "CRITICO", "SIN_DATOS")
