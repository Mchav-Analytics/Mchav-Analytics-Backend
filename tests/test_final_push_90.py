import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.report_service import generate_pdf_report_bytes
from app.api.v1.controllers.jql_controller import execute_custom_jql, JQLExecutionPayload

@pytest.mark.asyncio
async def test_generate_pdf_report_with_sprints():
    mock_db = MagicMock()
    proj = MagicMock(nombre="Proyecto Test", id_proyecto="P1")
    sprint1 = MagicMock(id_sprint="S1", nombre="Sprint 1", estado="CLOSED")
    sprint2 = MagicMock(id_sprint="S2", nombre="Sprint 2", estado="ACTIVE")
    
    def query_handler(model):
        m = MagicMock()
        m.filter.return_value.first.return_value = proj
        m.filter.return_value.order_by.return_value.limit.return_value.all.return_value = [sprint1, sprint2]
        return m

    mock_db.query.side_effect = query_handler

    with patch("app.repositories.project_repo.get_by_key", return_value=proj), \
         patch("app.repositories.project_repo.get", return_value=proj), \
         patch("app.repositories.sprint_repo.get_by_project", return_value=[sprint1, sprint2]), \
         patch("app.repositories.kpi_repo.get_general_kpi", return_value=MagicMock(health_score=85, velocity_total_sp=40, lead_time_promedio_dias=5.0, cycle_time_promedio_dias=2.0, throughput_issues=12, wic_activos=3, total_issues=15)), \
         patch("app.repositories.kpi_repo.get_sprint_kpi", return_value=MagicMock(velocity_total_sp=30, lead_time_promedio_dias=4.0, cycle_time_promedio_dias=1.5, throughput_issues=10)):
        
        pdf_bytes = generate_pdf_report_bytes(mock_db, "P1", usuario_nombre="Michael Salamanca")
        assert len(pdf_bytes) > 100

@pytest.mark.asyncio
async def test_execute_custom_jql_endpoint():
    mock_db = MagicMock()
    mock_req = MagicMock()
    payload = JQLExecutionPayload(jql="project = P1", max_results=10)

    jql_res = {
        "total": 1,
        "issues": [
            {
                "id": "1001",
                "key": "P1-1",
                "fields": {
                    "summary": "Fix bug",
                    "status": {"name": "Done"},
                    "assignee": {"displayName": "Dev 1"},
                    "issuetype": {"name": "Bug"}
                }
            }
        ]
    }

    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.api.v1.controllers.jql_controller.validate_jql_syntax"), \
         patch("app.api.v1.controllers.jql_controller.get_jira_auth_credentials", return_value=("http://jira", {})), \
         patch("app.datasources.jira_datasource.JiraDatasource.fetch_issues_jql", new_callable=AsyncMock, return_value=jql_res):
        
        res = await execute_custom_jql(payload, mock_req, mock_db)
        assert res["status"] == "success"
        assert len(res["issues"]) == 1
        assert res["issues"][0]["key"] == "P1-1"
