# tests/test_fase6_performance_score.py
# Pruebas automatizadas para la Fase 6: Performance Score, Cuadrantes y API REST

import pytest
from app.services.performance_score_engine import (
    calculate_performance_score,
    determine_quadrant
)

def test_performance_score_calculation():
    """
    Verifica que el algoritmo ponderado de 0-100 pts funcione correctamente.
    """
    score_data = calculate_performance_score(
        tickets_done=10,
        team_avg_tickets=8.0,
        sp_done=25.0,
        team_avg_sp=20.0,
        avg_cycle_time=2.5,
        team_avg_cycle_time=3.5,
        commitment_pct=90.0,
        bugs_reopened=1,
        total_bugs=5
    )

    score = score_data["final_score"]
    desglose = score_data["desglose"]

    assert 0.0 <= score <= 100.0
    assert "throughput_score" in desglose
    assert "velocity_score" in desglose
    assert "cycle_time_score" in desglose
    assert "commitment_score" in desglose
    assert "quality_score" in desglose
    assert desglose["quality_score"] == 80.0

def test_quadrant_determination():
    """
    Verifica la asignación adecuada de los 4 cuadrantes operativos.
    """
    # 1. ESTRELLA: Rápido (cycle <= avg) + Alta Calidad (>=75%)
    q_estrella = determine_quadrant(dev_cycle_time=2.0, team_avg_cycle_time=3.5, quality_score=85.0)
    assert q_estrella["codigo"] == "ESTRELLA"

    # 2. METODICO: Lento (cycle > avg) + Alta Calidad (>=75%)
    q_metodico = determine_quadrant(dev_cycle_time=5.0, team_avg_cycle_time=3.5, quality_score=85.0)
    assert q_metodico["codigo"] == "METODICO"

    # 3. ALTO_VOLUMEN: Rápido (cycle <= avg) + Baja Calidad (<75%)
    q_alto_vol = determine_quadrant(dev_cycle_time=2.0, team_avg_cycle_time=3.5, quality_score=60.0)
    assert q_alto_vol["codigo"] == "ALTO_VOLUMEN"

    # 4. ATASCADO: Lento (cycle > avg) + Baja Calidad (<75%)
    q_atascado = determine_quadrant(dev_cycle_time=6.0, team_avg_cycle_time=3.5, quality_score=50.0)
    assert q_atascado["codigo"] == "ATASCADO"
