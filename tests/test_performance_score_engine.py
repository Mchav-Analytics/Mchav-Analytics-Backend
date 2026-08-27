import pytest
from unittest.mock import MagicMock, patch
from app.services.performance_score_engine import (
    calculate_performance_score,
    determine_quadrant,
    calculate_team_performance_matrix
)

def test_calculate_performance_score_variations():
    # Test high score
    res_high = calculate_performance_score(
        tickets_done=10, team_avg_tickets=5.0,
        sp_done=30.0, team_avg_sp=15.0,
        avg_cycle_time=1.5, team_avg_cycle_time=3.0,
        commitment_pct=95.0, bugs_reopened=0, total_bugs=5
    )
    assert res_high["final_score"] > 80.0
    assert res_high["desglose"]["quality_score"] == 100.0

    # Test low score & zero averages
    res_low = calculate_performance_score(
        tickets_done=0, team_avg_tickets=0.0,
        sp_done=0.0, team_avg_sp=0.0,
        avg_cycle_time=10.0, team_avg_cycle_time=2.0,
        commitment_pct=10.0, bugs_reopened=2, total_bugs=0
    )
    assert res_low["final_score"] < 50.0
    assert res_low["desglose"]["quality_score"] == 50.0

def test_determine_quadrant_all_cases():
    q_estrella = determine_quadrant(dev_cycle_time=1.0, team_avg_cycle_time=2.0, quality_score=90.0)
    assert q_estrella["codigo"] == "ESTRELLA"

    q_metodico = determine_quadrant(dev_cycle_time=4.0, team_avg_cycle_time=2.0, quality_score=85.0)
    assert q_metodico["codigo"] == "METODICO"

    q_alto_vol = determine_quadrant(dev_cycle_time=1.5, team_avg_cycle_time=2.0, quality_score=60.0)
    assert q_alto_vol["codigo"] == "ALTO_VOLUMEN"

    q_atascado = determine_quadrant(dev_cycle_time=5.0, team_avg_cycle_time=2.0, quality_score=50.0)
    assert q_atascado["codigo"] == "ATASCADO"

def test_calculate_team_performance_matrix_no_devs():
    mock_db = MagicMock()
    mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = []
    
    matrix = calculate_team_performance_matrix(mock_db, proyecto_id="PROJ-01")
    assert matrix["team_summary"]["total_desarrolladores"] == 0
    assert matrix["developers"] == []

def test_calculate_team_performance_matrix_with_devs():
    mock_db = MagicMock()
    row1 = MagicMock(assignee_id="DEV-1", assignee_name="Dev Uno", assignee_email="dev1@test.com")
    row2 = MagicMock(assignee_id="DEV-2", assignee_name="Dev Dos", assignee_email="dev2@test.com")
    
    mock_db.query.return_value.filter.return_value.distinct.return_value.all.return_value = [row1, row2]
    
    scorecard_1 = {
        "kpis": {
            "throughput_issues": 10,
            "velocity_sp": 25.0,
            "cycle_time_promedio_dias": 1.5,
            "commitment_rate_pct": 95.0,
            "bugs_totales": 2,
            "bugs_resueltos": 2,
            "wip_actual": 1
        }
    }
    scorecard_2 = {
        "kpis": {
            "throughput_issues": 2,
            "velocity_sp": 5.0,
            "cycle_time_promedio_dias": 6.0,
            "commitment_rate_pct": 50.0,
            "bugs_totales": 4,
            "bugs_resueltos": 2,
            "wip_actual": 3
        }
    }
    
    with patch("app.services.performance_score_engine.get_developer_scorecard_data", side_effect=[scorecard_1, scorecard_2]):
        matrix = calculate_team_performance_matrix(mock_db, proyecto_id="PROJ-01")
        
    assert matrix["team_summary"]["total_desarrolladores"] == 2
    assert matrix["team_summary"]["top_performer"]["assignee_id"] == "DEV-1"
    assert len(matrix["developers"]) == 2
    assert matrix["developers"][0]["rank_posicion"] == 1
    assert matrix["developers"][0]["badge_honor"] == "🥇 Medalla de Oro"
