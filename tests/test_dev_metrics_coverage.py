import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime
from app.services.dev_metrics_service import (
    _get_previous_sprint_cycle_time,
    _get_previous_sprint_throughput,
    _calc_time_ago,
    _generate_ai_coach_tip
)

def test_calc_time_ago():
    assert _calc_time_ago({"cycle_time_days": 0.2}) == "Reciente"
    assert _calc_time_ago({"cycle_time_days": 0.9}) == "Hace unas horas"
    assert _calc_time_ago({"cycle_time_days": 1.8}) == "Hace 1 día"
    assert _calc_time_ago({"cycle_time_days": 5.0}) == "Hace 5 días"

def test_generate_ai_coach_tip():
    scorecard = {"cycle_time_personal": 2.0, "cycle_time_prev": 4.0, "wip_tickets": 4, "throughput_tickets": 5}
    urgent_qa = [{"key_issue": "BUG-1"}]
    active_dev = []

    tip1 = _generate_ai_coach_tip(scorecard, urgent_qa, active_dev)
    assert isinstance(tip1, str)
    assert len(tip1) > 10

    scorecard_worse = {"cycle_time_personal": 5.0, "cycle_time_prev": 2.0, "wip_tickets": 2, "throughput_tickets": 3}
    tip2 = _generate_ai_coach_tip(scorecard_worse, [], active_dev)
    assert isinstance(tip2, str)
    assert len(tip2) > 10

def test_get_previous_sprint_cycle_time_and_throughput():
    mock_db = MagicMock()
    sp1 = MagicMock(id_sprint="S1")
    sp2 = MagicMock(id_sprint="S2")
    
    mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [sp1, sp2]

    issue_prev = MagicMock(assignee_email="dev@mchav.com", assignee_id="DEV1")
    mock_db.query.return_value.filter.return_value.all.return_value = [issue_prev]

    with patch("app.services.dev_metrics_service.get_issue_cycle_time_days", return_value=3.0):
        ct_prev = _get_previous_sprint_cycle_time(mock_db, "P1", "dev@mchav.com")
        assert ct_prev == 3.0

    th_prev = _get_previous_sprint_throughput(mock_db, "P1", "dev@mchav.com")
    assert isinstance(th_prev, int)
