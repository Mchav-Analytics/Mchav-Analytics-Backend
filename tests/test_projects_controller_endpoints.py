import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from app.main import app
from app.core.security import get_current_user, sign_session_id
from app.models.auth import User, Role
from app.core.database import get_db
import app.models as models

client = TestClient(app)

@pytest.fixture(autouse=True)
def override_auth():
    mock_role = Role(nombre_rol="Administrador", scopes="jira:read,jira:sync,projects:write,admin")
    mock_user = User(id_usuario=1, email="admin@mchav.com", activo=True, rol=mock_role)
    mock_user.proyectos_asignados = []
    app.dependency_overrides[get_current_user] = lambda: mock_user
    yield
    app.dependency_overrides.pop(get_current_user, None)
    app.dependency_overrides.pop(get_db, None)

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.project_repo')
def test_get_projects_admin(mock_repo, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_user = MagicMock()
    mock_user.rol.nombre_rol = "administrador"
    mock_check_user.return_value = mock_user

    p1 = models.Proyecto(id_proyecto="P1", key_proyecto="P1", nombre="Proyecto 1", estado="Active")
    mock_repo.get_multi.return_value = [p1]

    res = client.get("/api/v1/projects", cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert len(res.json()) == 1

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
def test_get_projects_non_admin_with_assigned(mock_check_user, mock_user_id):
    mock_user_id.return_value = 2
    mock_user = MagicMock()
    mock_user.rol.nombre_rol = "desarrollador"
    proj_assigned = MagicMock()
    proj_assigned.id_proyecto = "P-ASSIGNED"
    mock_user.proyectos_asignados = [proj_assigned]
    mock_check_user.return_value = mock_user

    res = client.get("/api/v1/projects", cookies={"session_id": sign_session_id(2)})
    assert res.status_code == 200

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.project_repo')
def test_create_project_new_and_existing(mock_repo, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # 1. Existing project update
    existing = models.Proyecto(id_proyecto="EXISTING", key_proyecto="EXISTING", nombre="Old Name", estado="Active")
    mock_repo.get_by_key.return_value = existing

    res = client.post("/api/v1/projects", json={"key": "EXISTING", "name": "New Name"}, cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert existing.nombre == "New Name"
    assert mock_db.commit.called
    assert mock_db.refresh.called

    # 2. Brand new project
    mock_repo.get_by_key.return_value = None
    mock_db.query().filter().first.return_value = None
    res2 = client.post("/api/v1/projects", json={"key": "BRANDNEW", "name": "Brand New"}, cookies={"session_id": sign_session_id(1)})
    assert res2.status_code == 200
    assert mock_db.add.called

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.kpi_repo')
def test_get_project_kpis(mock_kpi_repo, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()

    mock_query = MagicMock()
    mock_kpi_repo.get_all_by_project.return_value = mock_query
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value.limit.return_value.all.return_value = [
        {"id_kpi": 1, "completed_sp": 10.0}
    ]

    res = client.get(
        "/api/v1/projects/PROJ-1/kpis?sprint_id=S1&fecha_inicio=2026-01-01T00:00:00Z&fecha_fin=2026-02-01T00:00:00Z&order=desc",
        cookies={"session_id": sign_session_id(1)}
    )
    assert res.status_code == 200
    assert mock_query.filter.call_count >= 3

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.mapping_repo')
def test_get_project_kpis_issues_detail(mock_mapping_repo, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()

    # Mapeo in_progress
    m = MagicMock()
    m.estado_jira = "In Progress"
    mock_mapping_repo.get_by_project_and_base.return_value = [m]

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # Create dummy issue with resolved_at and transitions
    now = datetime.now(timezone.utc)
    t = models.TransicionEstadoIssue(
        estado_anterior="To Do",
        estado_nuevo="In Progress",
        fecha_cambio=now - timedelta(days=2)
    )
    issue1 = models.Issue(
        id_jira="101",
        key_issue="PROJ-101",
        summary="Test Issue 1",
        status_actual="Done",
        story_points=5.0,
        created_at=now - timedelta(days=4),
        resolved_at=now - timedelta(days=1),
        assignee_name="Dev Uno",
        assignee_email="dev@mchav.com",
        issue_type="Story",
        priority="High"
    )
    issue1.transiciones = [t]
    issue1.sprint_activo = MagicMock(nombre="Sprint 1")

    mock_query = MagicMock()
    mock_query.filter.return_value = mock_query
    mock_query.order_by.return_value = mock_query
    mock_query.offset.return_value = mock_query
    mock_query.limit.return_value = mock_query
    mock_query.count.return_value = 1
    mock_query.all.return_value = [issue1]
    mock_db.query.return_value = mock_query

    res = client.get(
        "/api/v1/projects/PROJ-1/kpis/issues-detail?sprint_id=S1&metric_type=bugs&assignee_name=Dev&fecha_inicio=2026-01-01T00:00:00Z&fecha_fin=2026-03-01T00:00:00Z",
        cookies={"session_id": sign_session_id(1)}
    )
    assert res.status_code == 200
    data = res.json()
    assert len(data["issues"]) == 1
    assert data["issues"][0]["lead_time_days"] > 0
    assert data["issues"][0]["cycle_time_days"] > 0

    # Now metric_type throughput
    res2 = client.get(
        "/api/v1/projects/PROJ-1/kpis/issues-detail?metric_type=throughput&assignee_email=dev@mchav.com",
        cookies={"session_id": sign_session_id(1)}
    )
    assert res2.status_code == 200

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
def test_get_project_burnup_empty_and_active(mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()

    mock_db = MagicMock()
    app.dependency_overrides[get_db] = lambda: mock_db

    # 1. Project with no sprints returns []
    mock_db.query().filter().first.return_value = None
    mock_db.query().filter().order_by().first.return_value = None
    res = client.get("/api/v1/projects/NON_EXISTENT_PROJ/burnup", cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert res.json() == []

    # 2. Active sprint with issues and transitions
    now = datetime.now()
    sprint = models.Sprint(
        id_sprint=1,
        id_proyecto="PROJ-1",
        nombre="Sprint 1",
        estado="active",
        fecha_inicio=now - timedelta(days=3),
        fecha_fin=now + timedelta(days=3)
    )
    issue = models.Issue(
        id_jira="101",
        key_issue="PROJ-101",
        id_sprint=1,
        status_actual="Done",
        story_points=8.0,
        resolved_at=now - timedelta(days=1)
    )
    t = models.TransicionEstadoIssue(
        estado_nuevo="Done",
        fecha_cambio=now - timedelta(days=1)
    )
    issue.transiciones = [t]

    def mock_query(model):
        m = MagicMock()
        if model == models.Sprint:
            m.filter.return_value.first.return_value = sprint
        elif model == models.Issue:
            m.filter.return_value.all.return_value = [issue]
        return m
    mock_db.query.side_effect = mock_query

    res2 = client.get("/api/v1/projects/PROJ-1/burnup", cookies={"session_id": sign_session_id(1)})
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2) > 0
    assert data2[0]["alcance_total"] == 8.0

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.mapping_repo')
@patch('app.api.v1.controllers.projects_controller.calculate_and_save_kpis')
def test_save_project_mappings(mock_calc_kpis, mock_mapping_repo, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()

    payload = [
        {"estado_jira": "To Do", "estado_base": "TO_DO"},
        {"estado_jira": "In Dev", "estado_base": "IN_PROGRESS"},
        {"estado_jira": "Closed", "estado_base": "DONE"}
    ]
    res = client.post("/api/v1/projects/PROJ-1/mappings", json=payload, cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert mock_mapping_repo.delete_by_project.called
    assert mock_mapping_repo.create.call_count == 3
    assert mock_calc_kpis.called

@patch('app.api.v1.controllers.projects_controller.deps.get_current_user_id')
@patch('app.api.v1.controllers.projects_controller.deps.check_user_exists')
@patch('app.api.v1.controllers.projects_controller.project_repo')
@patch('app.api.v1.controllers.projects_controller.issue_repo')
def test_get_project_percentiles(mock_issue_repo, mock_proj_repo, mock_check_user, mock_user_id):
    mock_user_id.return_value = 1
    mock_check_user.return_value = MagicMock()

    mock_db = MagicMock()
    mock_db.query().filter().first.return_value = None
    mock_db.query().first.return_value = None
    app.dependency_overrides[get_db] = lambda: mock_db

    # 1. No project in DB returns default fallback
    mock_proj_repo.get_by_key.return_value = None
    mock_proj_repo.get.return_value = None

    res = client.get("/api/v1/projects/UNKNOWN/percentiles", cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 1
    assert data[0]["issue_type"] == "Story"

    # 2. Project exists with issues
    proj = models.Proyecto(id_proyecto="P1", key_proyecto="P1", nombre="P1")
    mock_proj_repo.get_by_key.return_value = proj
    mock_issue_repo.get_recent_resolved_issues_raw.return_value = [
        ("Story", 4.0, 2.0)
    ]

    res2 = client.get("/api/v1/projects/P1/percentiles", cookies={"session_id": sign_session_id(1)})
    assert res2.status_code == 200

@patch('app.api.v1.controllers.projects_controller.calculate_sprint_health')
def test_get_sprint_health_metrics(mock_calc_health):
    mock_calc_health.return_value = {"health_score": 85, "status": "GOOD"}

    res = client.get("/api/v1/projects/PROJ-1/health", cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert res.json()["health_score"] == 85

    # With sprint id
    res2 = client.get("/api/v1/projects/PROJ-1/sprints/S1/health", cookies={"session_id": sign_session_id(1)})
    assert res2.status_code == 200

@patch('app.api.v1.controllers.projects_controller.calculate_burndown_chart_data')
def test_get_burndown_chart(mock_calc_burndown):
    mock_calc_burndown.return_value = [{"day": "2026-01-01", "remaining_sp": 20}]

    res = client.get("/api/v1/projects/PROJ-1/burndown", cookies={"session_id": sign_session_id(1)})
    assert res.status_code == 200
    assert "data" in res.json()
