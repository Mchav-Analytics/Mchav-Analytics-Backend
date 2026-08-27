import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from app.api.v1.controllers.projects_controller import (
    get_project_percentiles,
    get_project_kpis_issues_detail
)

@pytest.mark.asyncio
async def test_get_project_percentiles_with_real_project():
    mock_db = MagicMock()
    mock_req = MagicMock()
    
    proj = MagicMock(id_proyecto="10001", key_proyecto="P1")

    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.repositories.project_repo.get_by_key", return_value=proj), \
         patch("app.repositories.mapping_repo.get_by_project_and_base", return_value=[]), \
         patch("app.repositories.issue_repo.get_recent_resolved_issues_raw", return_value=[("Story", 4.0, 2.0)]):
        
        results = await get_project_percentiles(mock_req, "P1", days=15, db=mock_db)
        assert isinstance(results, list)
        assert len(results) > 0

@pytest.mark.asyncio
async def test_get_project_kpis_issues_detail_filters():
    mock_db = MagicMock()
    mock_req = MagicMock()

    issue_bug = MagicMock(
        id_jira="J10", key_issue="K10", summary="Bug fix", status_actual="Done", story_points=2,
        created_at=datetime(2026, 1, 1), resolved_at=datetime(2026, 1, 2),
        sprint_activo=None, transiciones=[]
    )

    query_mock = MagicMock()
    query_mock.filter.return_value = query_mock
    query_mock.count.return_value = 1
    query_mock.order_by.return_value.offset.return_value.limit.return_value.all.return_value = [issue_bug]
    mock_db.query.return_value = query_mock

    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.repositories.mapping_repo.get_by_project_and_base", return_value=[]):
        
        detail = await get_project_kpis_issues_detail(
            mock_req,
            "P1",
            sprint_id="S1",
            assignee_email="dev@mchav.com",
            assignee_name="Dev",
            metric_type="bugs",
            fecha_inicio="2026-01-01T00:00:00Z",
            fecha_fin="2026-01-31T00:00:00Z",
            db=mock_db
        )
        assert detail["total_issues"] == 1
