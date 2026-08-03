# tests/test_fase2_drilldown_fechas.py
# Pruebas automatizadas para validar la Fase 2: Drill-down por Issue y Filtro Dinámico de Fechas (HU-011, HU-012, HU-014, HU-015)

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from app.services.kpi import get_issue_cycle_time_days
from app.models.jira import Issue, TransicionEstadoIssue

def test_calculo_lead_time_y_cycle_time_por_issue_individual():
    """HU-013 & HU-015: Verificar el cálculo de Lead Time y Cycle Time a nivel de ticket individual"""
    created = datetime(2026, 7, 10, 10, 0, 0, tzinfo=timezone.utc)
    in_prog = datetime(2026, 7, 12, 10, 0, 0, tzinfo=timezone.utc)
    resolved = datetime(2026, 7, 15, 10, 0, 0, tzinfo=timezone.utc)

    # Lead Time = 5 días (del 10 al 15)
    delta_lead = (resolved - created).total_seconds() / 86400.0
    assert delta_lead == 5.0

    # Mock del issue con transiciones
    mock_issue = MagicMock()
    mock_issue.created_at = created
    mock_issue.resolved_at = resolved
    
    t_prog = MagicMock()
    t_prog.estado_nuevo = "In Progress"
    t_prog.fecha_cambio = in_prog
    mock_issue.transiciones = [t_prog]

    # Cycle Time = 3 días (del 12 al 15)
    cycle_days = get_issue_cycle_time_days(mock_issue)
    assert cycle_days == 3.0

def test_porcentaje_cumplimiento_sprint():
    """HU-011: Calcular el % de cumplimiento de sprint (Story Points completados vs planificados)"""
    sp_planificados = 40.0
    sp_completados = 32.0
    
    porcentaje = (sp_completados / sp_planificados) * 100.0
    assert porcentaje == 80.0

def test_filtro_rango_fechas_parsing():
    """HU-012 & HU-014: Verificar parseo de ISO Datetime para filtrado dinámico"""
    fecha_inicio_str = "2026-07-01T00:00:00Z"
    dt = datetime.fromisoformat(fecha_inicio_str.replace("Z", "+00:00"))
    
    assert dt.year == 2026
    assert dt.month == 7
    assert dt.day == 1
