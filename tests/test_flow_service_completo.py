import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock
from app.services.flow_service import (
    FlowStateCategorizer,
    get_issue_flow_timeline,
    calculate_cycle_time_percentiles,
    calculate_flow_efficiency,
    detect_bottlenecks,
    get_blockers,
    get_aging_work,
    calculate_cfd_and_wip
)
import app.models as models

class MockTransition:
    def __init__(self, estado_anterior, estado_nuevo, fecha_cambio):
        self.estado_anterior = estado_anterior
        self.estado_nuevo = estado_nuevo
        self.fecha_cambio = fecha_cambio

class MockSprint:
    def __init__(self, nombre="Sprint 1"):
        self.nombre = nombre

class MockIssue:
    def __init__(self, key="TEST-1", created_at=None, resolved_at=None, status_actual="To Do", transiciones=None, id_proyecto="P1", id_sprint="S1", assignee_name="User"):
        self.id_issue = key
        self.key_issue = key
        self.summary = f"Summary {key}"
        self.created_at = created_at or datetime(2026, 1, 1, 10, 0)
        self.resolved_at = resolved_at
        self.status_actual = status_actual
        self.transiciones = transiciones or []
        self.id_proyecto = id_proyecto
        self.id_sprint = id_sprint
        self.assignee_name = assignee_name
        self.sprint_activo = MockSprint()

class MockMapping:
    def __init__(self, estado_jira, estado_base, id_proyecto="P1"):
        self.estado_jira = estado_jira
        self.estado_base = estado_base
        self.id_proyecto = id_proyecto

def make_mock_db(issues=None, mappings=None):
    mock_db = MagicMock()
    def query_mock(model):
        q = MagicMock()
        if model == models.MapeoEstado:
            q.filter.return_value.all.return_value = mappings or []
            q.all.return_value = mappings or []
        else:
            q.filter.return_value = q
            q.all.return_value = issues or []
        return q
    mock_db.query.side_effect = query_mock
    return mock_db

def test_flow_state_categorizer():
    mappings = [
        MockMapping("Hecho", "done"),
        MockMapping("En Desarrollo", "in_progress"),
        MockMapping("Code Review", "in_progress")
    ]
    mock_db = make_mock_db(mappings=mappings)
    categorizer = FlowStateCategorizer(mock_db, "P1")

    assert categorizer.categorize_state("") == "WAITING"
    assert categorizer.categorize_state("Hecho") == "DONE"
    assert categorizer.categorize_state("Code Review") == "WAITING"
    assert categorizer.categorize_state("En Desarrollo") == "ACTIVE"
    assert categorizer.categorize_state("Bloqueado") == "BLOCKED"
    assert categorizer.categorize_state("Listo") == "DONE"

def test_get_issue_flow_timeline_no_transitions():
    created = datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc)
    resolved = datetime(2026, 1, 2, 10, 0, tzinfo=timezone.utc)
    issue = MockIssue(created_at=created, resolved_at=resolved, status_actual="Done", transiciones=[])
    timeline = get_issue_flow_timeline(issue)

    assert len(timeline) == 1
    assert timeline[0]["state"] == "Done"
    assert timeline[0]["duration_seconds"] == 86400.0

def test_get_issue_flow_timeline_with_transitions():
    t0 = datetime(2026, 1, 1, 10, 0)
    t1 = datetime(2026, 1, 2, 10, 0)
    t2 = datetime(2026, 1, 4, 10, 0)
    trans = [
        MockTransition("To Do", "In Progress", t1),
        MockTransition("In Progress", "Done", t2)
    ]
    issue = MockIssue(created_at=t0, resolved_at=t2, status_actual="Done", transiciones=trans)
    timeline = get_issue_flow_timeline(issue)

    assert len(timeline) == 3
    assert timeline[0]["state"] == "To Do"
    assert timeline[1]["state"] == "In Progress"
    assert timeline[2]["state"] == "Done"

def test_calculate_cycle_time_percentiles_empty():
    mock_db = make_mock_db(issues=[])
    res = calculate_cycle_time_percentiles(mock_db, "P1")
    assert res["count"] == 0
    assert res["p50"] == 0

def test_calculate_cycle_time_percentiles_with_data():
    t0 = datetime(2026, 1, 1, 10, 0)
    t1 = datetime(2026, 1, 3, 10, 0)
    t2 = datetime(2026, 1, 5, 10, 0)
    
    issue1 = MockIssue("T1", created_at=t0, resolved_at=t1, transiciones=[
        MockTransition("To Do", "In Progress", t0),
        MockTransition("In Progress", "Done", t1)
    ])
    issue2 = MockIssue("T2", created_at=t0, resolved_at=t2, transiciones=[
        MockTransition("To Do", "In Progress", t0),
        MockTransition("In Progress", "Done", t2)
    ])

    mock_db = make_mock_db(issues=[issue1, issue2])

    res = calculate_cycle_time_percentiles(mock_db, "P1", sprint_id="S1")
    assert res["count"] == 2
    assert res["p50"] > 0
    assert res["p75"] >= res["p50"]

def test_calculate_flow_efficiency():
    t0 = datetime(2026, 1, 1, 10, 0)
    t1 = datetime(2026, 1, 2, 10, 0) # 1 day active
    t2 = datetime(2026, 1, 3, 10, 0) # 1 day waiting
    t3 = datetime(2026, 1, 4, 10, 0) # 1 day blocked
    
    issue = MockIssue("T1", created_at=t0, resolved_at=t3, transiciones=[
        MockTransition("To Do", "In Progress", t0),
        MockTransition("In Progress", "Code Review", t1),
        MockTransition("Code Review", "Blocked", t2),
        MockTransition("Blocked", "Done", t3)
    ])
    mock_db = make_mock_db(issues=[issue])

    res = calculate_flow_efficiency(mock_db, "P1")
    assert "active_pct" in res
    assert "waiting_pct" in res
    assert "blocked_pct" in res
    assert res["total_days"] > 0

def test_detect_bottlenecks():
    t0 = datetime(2026, 1, 1, 10, 0)
    t1 = datetime(2026, 1, 3, 10, 0)
    issue = MockIssue("T1", created_at=t0, resolved_at=t1, transiciones=[
        MockTransition("To Do", "In QA", t0),
        MockTransition("In QA", "Done", t1)
    ])
    mock_db = make_mock_db(issues=[issue])

    bottlenecks = detect_bottlenecks(mock_db, "P1")
    assert isinstance(bottlenecks, list)

def test_get_blockers_and_aging():
    now = datetime.now()
    blocked_issue = MockIssue("BLOCKED-1", created_at=now - timedelta(days=10), resolved_at=None, status_actual="Blocked")
    mock_db = make_mock_db(issues=[blocked_issue])

    blockers = get_blockers(mock_db, "P1")
    aging = get_aging_work(mock_db, "P1")

    assert isinstance(blockers, list)
    assert isinstance(aging, list)
    assert len(aging) >= 1
    assert aging[0]["aging_days"] >= 10

def test_calculate_cfd_and_wip():
    now = datetime.now()
    i1 = MockIssue("I1", created_at=now - timedelta(days=5), resolved_at=now, status_actual="Done")
    mock_db = make_mock_db(issues=[i1])

    cfd_res = calculate_cfd_and_wip(mock_db, "P1")
    assert "cfd" in cfd_res
    assert "wip" in cfd_res
    assert isinstance(cfd_res["cfd"], list)
