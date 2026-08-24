from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
import pytest

from app.services.kpi import get_issue_cycle_time_days, calculate_and_save_kpis

# Helper mock classes for testing issue transitions without DB dependency
class MockTransition:
    def __init__(self, estado_nuevo, fecha_cambio):
        self.estado_nuevo = estado_nuevo
        self.fecha_cambio = fecha_cambio

class MockIssue:
    def __init__(self, created_at, resolved_at=None, transiciones=None, story_points=0.0):
        self.created_at = created_at
        self.resolved_at = resolved_at
        self.transiciones = transiciones or []
        self.story_points = story_points

class MockProject:
    def __init__(self, id_proyecto, key_proyecto, nombre):
        self.id_proyecto = id_proyecto
        self.key_proyecto = key_proyecto
        self.nombre = nombre

class MockMapping:
    def __init__(self, estado_jira, estado_base):
        self.estado_jira = estado_jira
        self.estado_base = estado_base

class MockSprint:
    def __init__(self, id_sprint, nombre, estado, fecha_inicio=None, fecha_fin=None, fecha_finalizacion=None):
        self.id_sprint = id_sprint
        self.nombre = nombre
        self.estado = estado
        self.fecha_inicio = fecha_inicio
        self.fecha_fin = fecha_fin
        self.fecha_finalizacion = fecha_finalizacion

def test_tiempo_ciclo_ticket_no_resuelto():
    """Un issue que no está resuelto (resolved_at es None) debe retornar 0.0."""
    created = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    issue = MockIssue(created_at=created, resolved_at=None)
    assert get_issue_cycle_time_days(issue) == 0.0

def test_tiempo_ciclo_sin_transiciones_progreso():
    """Si un issue no tiene transiciones a 'In Progress', el cálculo se hace con resolved_at - created_at."""
    created = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    resolved = datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc)
    transitions = [
        MockTransition(estado_nuevo="Done", fecha_cambio=resolved)
    ]
    issue = MockIssue(created_at=created, resolved_at=resolved, transiciones=transitions)
    assert get_issue_cycle_time_days(issue) == 4.0

def test_tiempo_ciclo_con_transicion_progreso():
    """Debe usar la primera fecha de transición a un estado de tipo 'In Progress'."""
    created = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    in_progress = datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc)
    another_progress = datetime(2026, 7, 4, 10, 0, tzinfo=timezone.utc)
    resolved = datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc)
    
    transitions = [
        MockTransition(estado_nuevo="To Do", fecha_cambio=created),
        MockTransition(estado_nuevo="In Progress", fecha_cambio=in_progress),
        MockTransition(estado_nuevo="In Development", fecha_cambio=another_progress),
        MockTransition(estado_nuevo="Done", fecha_cambio=resolved)
    ]
    issue = MockIssue(created_at=created, resolved_at=resolved, transiciones=transitions)
    assert get_issue_cycle_time_days(issue) == 3.0

def test_tiempo_ciclo_insensible_mayusculas():
    """Prueba que los estados por defecto funcionen y sean insensibles a mayúsculas/minúsculas."""
    created = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    in_progress = datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)
    resolved = datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc)
    
    transitions = [
        MockTransition(estado_nuevo="EN PROGRESO", fecha_cambio=in_progress),
        MockTransition(estado_nuevo="Done", fecha_cambio=resolved)
    ]
    issue = MockIssue(created_at=created, resolved_at=resolved, transiciones=transitions)
    assert get_issue_cycle_time_days(issue) == 3.0

def test_tiempo_ciclo_transiciones_desordenadas():
    """El orden de las transiciones no debe alterar el resultado; deben ordenarse cronológicamente."""
    created = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    in_progress = datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc)
    resolved = datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc)
    
    transitions = [
        MockTransition(estado_nuevo="Done", fecha_cambio=resolved),
        MockTransition(estado_nuevo="In Progress", fecha_cambio=in_progress),
        MockTransition(estado_nuevo="To Do", fecha_cambio=created),
    ]
    issue = MockIssue(created_at=created, resolved_at=resolved, transiciones=transitions)
    assert get_issue_cycle_time_days(issue) == 3.0

def test_tiempo_ciclo_estados_personalizados():
    """Debe permitir inyectar estados de progreso personalizados."""
    created = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    custom_in_progress = datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)
    resolved = datetime(2026, 7, 5, 10, 0, tzinfo=timezone.utc)
    
    transitions = [
        MockTransition(estado_nuevo="CustomState", fecha_cambio=custom_in_progress),
        MockTransition(estado_nuevo="Done", fecha_cambio=resolved)
    ]
    issue = MockIssue(created_at=created, resolved_at=resolved, transiciones=transitions)
    assert get_issue_cycle_time_days(issue) == 4.0
    assert get_issue_cycle_time_days(issue, in_progress_statuses={"customstate"}) == 3.0

@patch('app.services.kpi.project_repo')
@patch('app.services.kpi.mapping_repo')
@patch('app.services.kpi.issue_repo')
@patch('app.services.kpi.sprint_repo')
@patch('app.services.kpi.kpi_repo')
def test_calculo_y_guardado_kpis_matematica(
    mock_kpi_repo,
    mock_sprint_repo,
    mock_issue_repo,
    mock_mapping_repo,
    mock_project_repo
):
    """Verifica que la integración de repositorios y la matemática general/sprints sea exacta."""
    db_session = MagicMock()
    proyecto_id = "PROJ-1"
    
    mock_project_repo.get.return_value = MockProject(proyecto_id, "KEY", "Nombre Proyecto")
    mock_mapping_repo.get_by_project_and_base.return_value = [
        MockMapping(estado_jira="Desarrollando", estado_base="IN_PROGRESS")
    ]
    
    created_1 = datetime(2026, 7, 1, 10, 0, tzinfo=timezone.utc)
    progress_1 = datetime(2026, 7, 3, 10, 0, tzinfo=timezone.utc)
    resolved_1 = datetime(2026, 7, 6, 10, 0, tzinfo=timezone.utc)
    issue_1 = MockIssue(
        created_at=created_1,
        resolved_at=resolved_1,
        story_points=3.0,
        transiciones=[
            MockTransition(estado_nuevo="Desarrollando", fecha_cambio=progress_1)
        ]
    )
    
    created_2 = datetime(2026, 7, 2, 10, 0, tzinfo=timezone.utc)
    resolved_2 = datetime(2026, 7, 4, 10, 0, tzinfo=timezone.utc)
    issue_2 = MockIssue(
        created_at=created_2,
        resolved_at=resolved_2,
        story_points=5.0,
        transiciones=[]
    )
    
    issue_3 = MockIssue(
        created_at=created_1,
        resolved_at=None,
        story_points=8.0
    )
    
    mock_issue_repo.get_resolved_stats_by_project.return_value = (8.0, 2, 3.5, 2.5)
    mock_kpi_repo.get_general_kpi.return_value = None
    
    sprint_1 = MockSprint(
        id_sprint="S-1",
        nombre="Sprint 1",
        estado="completado",
        fecha_inicio=datetime(2026, 7, 1, 0, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 7, 5, 0, 0, tzinfo=timezone.utc),
        fecha_finalizacion=datetime(2026, 7, 5, 0, 0, tzinfo=timezone.utc)
    )
    sprint_2 = MockSprint(
        id_sprint="S-2",
        nombre="Sprint 2",
        estado="completado",
        fecha_inicio=datetime(2026, 7, 6, 0, 0, tzinfo=timezone.utc),
        fecha_fin=datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc),
        fecha_finalizacion=datetime(2026, 7, 10, 0, 0, tzinfo=timezone.utc)
    )
    mock_sprint_repo.get_by_project.return_value = [sprint_2, sprint_1]
    
    mock_issue_repo.get_resolved_stats_by_sprint.side_effect = lambda db, sprint_id, status_set: {
        "S-1": (5.0, 1, 2.0, 2.0),
        "S-2": (3.0, 1, 5.0, 3.0)
    }.get(sprint_id, (0.0, 0, 0.0, 0.0))
    
    mock_kpi_repo.get_sprint_kpi.return_value = None
    
    calculate_and_save_kpis(db_session, proyecto_id)
    
    calls = mock_kpi_repo.create.call_args_list
    assert len(calls) == 3
    
    general_call = next(c for c in calls if c.kwargs['obj_in'].get('id_sprint') is None)
    s1_call = next(c for c in calls if c.kwargs['obj_in'].get('id_sprint') == "S-1")
    s2_call = next(c for c in calls if c.kwargs['obj_in'].get('id_sprint') == "S-2")
    
    gen_data = general_call.kwargs['obj_in']
    assert gen_data['id_proyecto'] == proyecto_id
    assert gen_data['velocity_total_sp'] == 8.0
    assert gen_data['velocity_promedio_historico'] == 8.0
    assert gen_data['throughput_issues'] == 2
    assert pytest.approx(gen_data['lead_time_promedio_dias']) == 3.5
    assert pytest.approx(gen_data['cycle_time_promedio_dias']) == 2.5
    assert isinstance(gen_data['fecha_calculo'], datetime)
    
    s1_data = s1_call.kwargs['obj_in']
    assert s1_data['id_proyecto'] == proyecto_id
    assert s1_data['velocity_total_sp'] == 5.0
    assert s1_data['velocity_promedio_historico'] == 5.0
    assert s1_data['throughput_issues'] == 1
    assert pytest.approx(s1_data['lead_time_promedio_dias']) == 2.0
    assert pytest.approx(s1_data['cycle_time_promedio_dias']) == 2.0
    assert isinstance(s1_data['fecha_calculo'], datetime)
    
    s2_data = s2_call.kwargs['obj_in']
    assert s2_data['id_proyecto'] == proyecto_id
    assert s2_data['velocity_total_sp'] == 3.0
    assert s2_data['velocity_promedio_historico'] == 4.0
    assert s2_data['throughput_issues'] == 1
    assert pytest.approx(s2_data['lead_time_promedio_dias']) == 5.0
    assert pytest.approx(s2_data['cycle_time_promedio_dias']) == 3.0
    assert isinstance(s2_data['fecha_calculo'], datetime)

def test_consultas_estadisticas_resueltas_base_datos():
    """Prueba de integración real con base de datos SQLite en memoria para verificar la compilación y matemática SQL."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from app.core.database import Base
    from app.repositories import issue_repo
    import app.models as models

    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    
    db = TestingSessionLocal()
    try:
        proyecto = models.Proyecto(id_proyecto="PROJ-TEST", key_proyecto="TST", nombre="Test Project")
        db.add(proyecto)
        
        sprint = models.Sprint(id_sprint="SPR-TEST", id_proyecto="PROJ-TEST", nombre="Sprint Test", estado="completado")
        db.add(sprint)
        
        created_1 = datetime(2026, 7, 1, 10, 0)
        resolved_1 = datetime(2026, 7, 6, 10, 0)
        issue_1 = models.Issue(
            id_jira="ISS-1",
            key_issue="TST-1",
            id_proyecto="PROJ-TEST",
            id_sprint="SPR-TEST",
            summary="Issue 1",
            status_actual="Done",
            story_points=3.0,
            created_at=created_1,
            resolved_at=resolved_1
        )
        db.add(issue_1)
        
        t1 = models.TransicionEstadoIssue(
            id_jira="ISS-1",
            estado_anterior="To Do",
            estado_nuevo="Desarrollo",
            fecha_cambio=datetime(2026, 7, 3, 10, 0)
        )
        db.add(t1)
        
        created_2 = datetime(2026, 7, 2, 10, 0)
        resolved_2 = datetime(2026, 7, 4, 10, 0)
        issue_2 = models.Issue(
            id_jira="ISS-2",
            key_issue="TST-2",
            id_proyecto="PROJ-TEST",
            id_sprint="SPR-TEST",
            summary="Issue 2",
            status_actual="Done",
            story_points=5.0,
            created_at=created_2,
            resolved_at=resolved_2
        )
        db.add(issue_2)
        db.commit()
        
        in_progress_statuses = {"desarrollo"}
        
        proj_stats = issue_repo.get_resolved_stats_by_project(db, "PROJ-TEST", in_progress_statuses)
        assert proj_stats[0] == 8.0
        assert proj_stats[1] == 2
        assert pytest.approx(proj_stats[2]) == 3.5
        assert pytest.approx(proj_stats[3]) == 2.5
        
        sprint_stats = issue_repo.get_resolved_stats_by_sprint(db, "SPR-TEST", in_progress_statuses)
        assert sprint_stats[0] == 8.0
        assert sprint_stats[1] == 2
        assert pytest.approx(sprint_stats[2]) == 3.5
        assert pytest.approx(sprint_stats[3]) == 2.5
        
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
