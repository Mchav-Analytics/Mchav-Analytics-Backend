import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from app.api.v1.controllers.projects_controller import (
    get_sprint_health_metrics,
    get_projects,
    create_project,
    get_project_kpis,
    get_project_kpis_issues_detail,
    get_project_sprints,
    get_project_unique_statuses,
    get_project_mappings,
    save_project_mappings,
    get_project_percentiles,
    get_burndown_chart,
    get_burnup_chart,
    get_cfd_chart
)
import app.models as models

@pytest.mark.asyncio
async def test_get_sprint_health_metrics():
    mock_db = MagicMock()
    with patch("app.api.v1.controllers.projects_controller.calculate_sprint_health", return_value={"health": 80}):
        res = await get_sprint_health_metrics("P1", "S1", mock_db)
        assert res == {"health": 80}

    # Exception fallback
    with patch("app.api.v1.controllers.projects_controller.calculate_sprint_health", side_effect=[Exception("Error"), {"health": 0}]):
        res_fb = await get_sprint_health_metrics("P1", "S1", mock_db)
        assert res_fb == {"health": 0}

@pytest.mark.asyncio
async def test_get_projects_admin_and_user():
    mock_db = MagicMock()
    mock_req = MagicMock()
    
    # Admin role
    admin_user = MagicMock(rol=MagicMock(nombre_rol="Administrador"))
    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists", return_value=admin_user), \
         patch("app.repositories.project_repo.get_multi", return_value=["proj1"]):
        projs = await get_projects(mock_req, db=mock_db)
        assert projs == ["proj1"]

    # Non-admin user with assigned projects
    normal_user = MagicMock(rol=MagicMock(nombre_rol="Líder"), proyectos_asignados=[MagicMock(id_proyecto="P10")])
    mock_db.query.return_value.filter.return_value.all.return_value = ["proj_assigned"]
    with patch("app.api.v1.deps.get_current_user_id", return_value=2), \
         patch("app.api.v1.deps.check_user_exists", return_value=normal_user):
        projs_assigned = await get_projects(mock_req, db=mock_db)
        assert projs_assigned == ["proj_assigned"]

@pytest.mark.asyncio
async def test_create_project_new_and_existing():
    mock_db = MagicMock()
    mock_req = MagicMock()
    
    # Existing project
    existing_proj = MagicMock(nombre="Viejo")
    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.repositories.project_repo.get_by_key", return_value=existing_proj):
        res_ex = await create_project(mock_req, {"key": "P1", "name": "Nuevo"}, mock_db)
        assert res_ex.nombre == "Nuevo"

    # New project
    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.repositories.project_repo.get_by_key", return_value=None):
        mock_db.query.return_value.filter.return_value.first.return_value = None
        res_new = await create_project(mock_req, {"key": "P2", "name": "Proyecto 2"}, mock_db)
        assert mock_db.add.called

@pytest.mark.asyncio
async def test_get_project_kpis():
    mock_db = MagicMock()
    mock_req = MagicMock()
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.order_by.return_value.offset.return_value.limit.return_value.all.return_value = ["kpi1"]
    
    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.repositories.kpi_repo.get_all_by_project", return_value=query_mock):
        kpis = await get_project_kpis(mock_req, "P1", sprint_id="S1", fecha_inicio="2026-01-01T00:00:00Z", fecha_fin="2026-01-31T00:00:00Z", db=mock_db)
        assert kpis == ["kpi1"]

@pytest.mark.asyncio
async def test_get_project_kpis_issues_detail():
    mock_db = MagicMock()
    mock_req = MagicMock()
    
    issue1 = MagicMock(
        id_jira="J1", key_issue="K1", summary="Sum", status_actual="Done", story_points=3,
        created_at=datetime(2026, 1, 1, 0, 0, 0), resolved_at=datetime(2026, 1, 3, 0, 0, 0),
        sprint_activo=MagicMock(nombre="S1"), transiciones=[]
    )
    
    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.count.return_value = 1
    query_mock.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [issue1]
    mock_db.query.return_value = query_mock
    
    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.repositories.mapping_repo.get_by_project_and_base", return_value=[]):
        detail = await get_project_kpis_issues_detail(mock_req, "P1", metric_type="lead_time", db=mock_db)
        assert detail["total_issues"] == 1
        assert len(detail["issues"]) == 1
        assert detail["issues"][0]["lead_time_days"] == 2.0

@pytest.mark.asyncio
async def test_get_project_sprints_statuses_mappings():
    mock_db = MagicMock()
    mock_req = MagicMock()
    
    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.repositories.sprint_repo.get_by_project", return_value=["s1"]):
        sprints = await get_project_sprints(mock_req, "P1", db=mock_db)
        assert sprints == ["s1"]

    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.repositories.issue_repo.get_distinct_statuses_by_project", return_value=[("Done",)]), \
         patch("app.repositories.transition_repo.get_distinct_new_statuses_by_project", return_value=[("In Progress",)]), \
         patch("app.repositories.transition_repo.get_distinct_prev_statuses_by_project", return_value=[("To Do",)]):
        statuses = await get_project_unique_statuses(mock_req, "P1", db=mock_db)
        assert statuses == ["Done", "In Progress", "To Do"]

    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.repositories.mapping_repo.get_by_project", return_value=["m1"]):
        mappings = await get_project_mappings(mock_req, "P1", db=mock_db)
        assert mappings == ["m1"]

@pytest.mark.asyncio
async def test_save_project_mappings():
    mock_db = MagicMock()
    mock_req = MagicMock()
    
    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.repositories.mapping_repo.delete_by_project"), \
         patch("app.repositories.mapping_repo.create"), \
         patch("app.api.v1.controllers.projects_controller.calculate_and_save_kpis"):
        res = await save_project_mappings(mock_req, "P1", [{"estado_jira": "Listo", "estado_base": "DONE"}], mock_db)
        assert "éxito" in res["message"]

@pytest.mark.asyncio
async def test_get_project_percentiles_and_burndown():
    mock_db = MagicMock()
    mock_req = MagicMock()
    
    # Percentiles project not found fallback
    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.repositories.project_repo.get_by_key", return_value=None), \
         patch("app.repositories.project_repo.get", return_value=None):
        q_mock = MagicMock()
        q_mock.filter.return_value.first.return_value = None
        q_mock.first.return_value = None
        mock_db.query.return_value = q_mock
        
        perc_fb = await get_project_percentiles(mock_req, "INVALID", db=mock_db)
        assert len(perc_fb) == 2

    # Burndown chart
    with patch("app.api.v1.controllers.projects_controller.calculate_burndown_chart_data", return_value=[{"dia": 1}]):
        bd = await get_burndown_chart("P1", "S1", mock_db)
        assert bd["data"] == [{"dia": 1}]

@pytest.mark.asyncio
async def test_get_burnup_and_cfd_charts():
    mock_db = MagicMock()
    with patch("app.api.v1.controllers.projects_controller.calculate_burnup_chart_data", return_value=[{"dia": 1}]):
        bu = await get_burnup_chart("P1", "S1", mock_db)
        assert bu["data"] == [{"dia": 1}]

    with patch("app.api.v1.controllers.projects_controller.calculate_cfd_chart_data", return_value=[{"dia": 1}]):
        cfd = await get_cfd_chart("P1", "S1", mock_db)
        assert cfd["data"] == [{"dia": 1}]

