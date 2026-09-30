import pytest
from unittest.mock import MagicMock, patch
from app.services.percentiles_service import calculate_percentiles
from app.services.performance_score_engine import (
    calculate_performance_score,
    determine_quadrant,
    calculate_team_performance_matrix
)
import app.models as models

def test_percentiles_empty():
    res = calculate_percentiles([])
    assert res == []

def test_percentiles_less_than_five_samples():
    raw_data = [
        ("Story", 10.0, 5.0),
        ("Story", 8.0, 4.0),
        ("Story", 12.0, 6.0),
    ]
    res = calculate_percentiles(raw_data)
    assert len(res) == 1
    item = res[0]
    assert item["issue_type"] == "Story"
    assert item["has_enough_data"] is False
    assert item["count"] == 3
    assert item["lead_time"]["avg"] == 10.0
    assert item["cycle_time"]["avg"] == 5.0
    assert "p50" not in item["lead_time"]

def test_percentiles_five_or_more_samples_and_multiple_types():
    raw_data = [
        ("Bug", 2.0, 1.0),
        ("Bug", 4.0, 2.0),
        ("Bug", 6.0, 3.0),
        ("Bug", 8.0, 4.0),
        ("Bug", 10.0, 5.0),
        (None, 1.0, 1.0),
    ]
    res = calculate_percentiles(raw_data)
    # Bug has 5 items
    bug_item = next(r for r in res if r["issue_type"] == "Bug")
    assert bug_item["has_enough_data"] is True
    assert bug_item["count"] == 5
    assert bug_item["lead_time"]["avg"] == 6.0
    assert bug_item["cycle_time"]["avg"] == 3.0
    assert "p25" in bug_item["lead_time"]
    assert "p50" in bug_item["lead_time"]
    assert "p75" in bug_item["lead_time"]
    assert "p90" in bug_item["lead_time"]
    assert "p50" in bug_item["cycle_time"]

    # Desconocido has 1 item
    desc_item = next(r for r in res if r["issue_type"] == "Desconocido")
    assert desc_item["has_enough_data"] is False
    assert desc_item["count"] == 1

def test_calculate_performance_score_variants():
    # Normal case
    score1 = calculate_performance_score(
        tickets_done=10,
        team_avg_tickets=8.0,
        sp_done=30.0,
        team_avg_sp=25.0,
        avg_cycle_time=2.5,
        team_avg_cycle_time=3.0,
        commitment_pct=95.0,
        bugs_reopened=1,
        total_bugs=10
    )
    assert 0.0 <= score1["final_score"] <= 100.0
    assert "desglose" in score1

    # Edge cases: 0 team averages, cycle time <= 0, ct_ratio > 1.0, 0 total bugs
    score2 = calculate_performance_score(
        tickets_done=0,
        team_avg_tickets=0.0,
        sp_done=0.0,
        team_avg_sp=0.0,
        avg_cycle_time=0.0,
        team_avg_cycle_time=0.0,
        commitment_pct=-10.0,
        bugs_reopened=0,
        total_bugs=0
    )
    assert 0.0 <= score2["final_score"] <= 100.0

    score3 = calculate_performance_score(
        tickets_done=5,
        team_avg_tickets=10.0,
        sp_done=10.0,
        team_avg_sp=20.0,
        avg_cycle_time=5.0,
        team_avg_cycle_time=2.0,
        commitment_pct=110.0,
        bugs_reopened=2,
        total_bugs=0
    )
    assert 0.0 <= score3["final_score"] <= 100.0

def test_determine_quadrant_all_four():
    # ESTRELLA: fast + high quality
    q1 = determine_quadrant(dev_cycle_time=2.0, team_avg_cycle_time=3.0, quality_score=90.0)
    assert q1["codigo"] == "ESTRELLA"

    # METODICO: slow + high quality
    q2 = determine_quadrant(dev_cycle_time=4.0, team_avg_cycle_time=3.0, quality_score=85.0)
    assert q2["codigo"] == "METODICO"

    # ALTO_VOLUMEN: fast + low quality
    q3 = determine_quadrant(dev_cycle_time=1.5, team_avg_cycle_time=3.0, quality_score=60.0)
    assert q3["codigo"] == "ALTO_VOLUMEN"

    # ATASCADO: slow + low quality
    q4 = determine_quadrant(dev_cycle_time=5.0, team_avg_cycle_time=3.0, quality_score=50.0)
    assert q4["codigo"] == "ATASCADO"

def test_calculate_team_performance_matrix_empty():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []
    
    with patch("app.services.performance_score_engine.resolve_project_id", return_value="PROJ-01"):
        res = calculate_team_performance_matrix(mock_db, "PROJ-01")
        assert res["team_summary"]["total_desarrolladores"] == 0
        assert res["developers"] == []

def test_calculate_team_performance_matrix_with_developers():
    mock_db = MagicMock()
    
    dev1 = MagicMock()
    dev1.assignee_id = "user1"
    dev1.assignee_name = "Dev One"
    dev1.assignee_email = "dev1@test.com"

    dev2 = MagicMock()
    dev2.assignee_id = "user2"
    dev2.assignee_name = "Dev Two"
    dev2.assignee_email = "dev2@test.com"

    mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = [dev1, dev2]

    def mock_scorecard(db, proj_id, email_or_assignee_id):
        if "user1" in email_or_assignee_id or "dev1" in email_or_assignee_id:
            return {
                "kpis": {
                    "throughput_issues": 10,
                    "velocity_sp": 30.0,
                    "cycle_time_promedio_dias": 2.0,
                    "commitment_rate_pct": 95.0,
                    "bugs_totales": 2,
                    "bugs_resueltos": 2,
                    "wip_actual": 1
                }
            }
        else:
            return {
                "throughput_issues": 4,
                "velocity_sp": 10.0,
                "cycle_time_promedio_dias": 5.0,
                "commitment_rate_pct": 70.0,
                "bugs_totales": 3,
                "bugs_resueltos": 1,
                "wip_actual": 2
            }

    with patch("app.services.performance_score_engine.resolve_project_id", return_value="PROJ-01"), \
         patch("app.services.performance_score_engine.get_developer_scorecard_data", side_effect=mock_scorecard):
        
        matrix = calculate_team_performance_matrix(mock_db, "PROJ-01")
        assert matrix["team_summary"]["total_desarrolladores"] == 2
        assert len(matrix["developers"]) == 2
        assert matrix["developers"][0]["rank_posicion"] == 1
        assert "Medalla de Oro" in matrix["developers"][0]["badge_honor"]
        assert len(matrix["developers"][0]["explicacion_razones"]) > 0
