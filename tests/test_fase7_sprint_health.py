# tests/test_fase7_sprint_health.py
# Pruebas automatizadas para la Fase 7: Predictibilidad de Sprint, Flow Efficiency y Health Score

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from app.services.sprint_health_service import calculate_sprint_health
import app.models as models

class MockSprint:
    def __init__(self, id_sprint="SP-1", fecha_inicio=None):
        self.id_sprint = id_sprint
        self.fecha_inicio = fecha_inicio or datetime(2026, 1, 1, 9, 0, tzinfo=timezone.utc)

class MockIssue:
    def __init__(self, key="KEY-1", story_points=5.0, status_actual="Done", created_at=None, updated_at=None, resolved_at=None, transiciones=None):
        self.id_issue = key
        self.key_issue = key
        self.story_points = story_points
        self.status_actual = status_actual
        self.created_at = created_at or datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc)
        self.updated_at = updated_at or datetime(2026, 1, 2, 8, 0, tzinfo=timezone.utc)
        self.resolved_at = resolved_at or datetime(2026, 1, 3, 8, 0, tzinfo=timezone.utc)
        self.transiciones = transiciones or []
        self.id_proyecto = "P1"
        self.id_sprint = "SP-1"

def test_sprint_health_calculation_db_none():
    res = calculate_sprint_health(db=None, proyecto_id="PROJ-01")
    assert "health_score" in res
    assert "metrics" in res
    assert res["diagnostico"] in ("EXCELENTE", "ACEPTABLE", "CRITICO", "SIN_DATOS")

def test_sprint_health_with_empty_issues():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.all.return_value = []
    mock_db.query.return_value.all.return_value = []
    res = calculate_sprint_health(db=mock_db, proyecto_id="P1", sprint_id="SP-1")
    assert res["health_score"] == 78
    assert res["diagnostico"] == "ACEPTABLE"

def test_sprint_health_calculation_real_issues():
    mock_db = MagicMock()
    sprint_start = datetime(2026, 1, 2, 9, 0, tzinfo=timezone.utc)
    sprint = MockSprint("SP-1", fecha_inicio=sprint_start)

    # Issue 1: Done before sprint
    i1 = MockIssue("I1", story_points=8.0, status_actual="Done", created_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc))
    # Issue 2: Added mid-sprint (Scope creep)
    i2 = MockIssue("I2", story_points=5.0, status_actual="In Progress", created_at=datetime(2026, 1, 5, 8, 0, tzinfo=timezone.utc))
    # Issue 3: In Review
    i3 = MockIssue("I3", story_points=3.0, status_actual="In Review", created_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc))
    # Issue 4: Cancelled mid-sprint
    i4 = MockIssue("I4", story_points=2.0, status_actual="Cancelado", created_at=datetime(2026, 1, 1, 8, 0, tzinfo=timezone.utc), updated_at=datetime(2026, 1, 4, 8, 0, tzinfo=timezone.utc))

    def query_mock(model):
        q = MagicMock()
        if model == models.Sprint:
            q.filter.return_value.first.return_value = sprint
        else:
            q.filter.return_value.all.return_value = [i1, i2, i3, i4]
            q.filter.return_value = q
            q.all.return_value = [i1, i2, i3, i4]
        return q

    mock_db.query.side_effect = query_mock

    res = calculate_sprint_health(db=mock_db, proyecto_id="P1", sprint_id="SP-1")

    assert "health_score" in res
    assert res["health_score"] > 0
    assert "metrics" in res
    assert res["metrics"]["commitment_reliability_pct"] >= 0
    assert res["metrics"]["scope_creep_pct"] >= 0
    assert "bottleneck_insight" in res
    assert res["diagnostico"] in ("EXCELENTE", "ACEPTABLE", "CRITICO")
