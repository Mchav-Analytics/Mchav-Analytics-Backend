import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.api.v1.controllers.jira_controller import (
    get_issue_transitions,
    transition_issue,
    jira_webhook,
    IssueTransitionRequest,
    JiraWebhookPayload
)
import app.models as models

@pytest.mark.asyncio
async def test_get_issue_transitions():
    mock_db = MagicMock()
    mock_req = MagicMock()

    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.api.v1.controllers.jira_controller.get_jira_auth_credentials", return_value=("http://jira/rest/api/3", {})), \
         patch("app.datasources.jira_datasource.JiraDatasource.fetch_issue_transitions", new_callable=AsyncMock, return_value={"transitions": []}):
        res = await get_issue_transitions("K-1", mock_req, mock_db)
        assert res == {"transitions": []}

@pytest.mark.asyncio
async def test_transition_issue():
    mock_db = MagicMock()
    mock_req = MagicMock()
    
    db_issue = MagicMock(id_jira="J1", key_issue="K1", status_actual="To Do")
    mock_db.query.return_value.filter.return_value.first.return_value = db_issue

    payload = IssueTransitionRequest(target_status="Done", transition_id="31")

    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.api.v1.controllers.jira_controller.get_jira_auth_credentials", return_value=("http://jira/rest/api/3", {})), \
         patch("app.datasources.jira_datasource.JiraDatasource.post_issue_transition", new_callable=AsyncMock):
        res = await transition_issue("K1", payload, mock_req, mock_db)
        assert res["status"] == "success"
        assert res["new_status"] == "Done"

@pytest.mark.asyncio
async def test_transition_issue_without_transition_id():
    mock_db = MagicMock()
    mock_req = MagicMock()
    
    db_issue = MagicMock(id_jira="J1", key_issue="K1", status_actual="To Do")
    mock_db.query.return_value.filter.return_value.first.return_value = db_issue

    payload = IssueTransitionRequest(target_status="Done", transition_id=None)

    valid_trans = {
        "transitions": [
            {"id": "41", "name": "Finalizar Tarea", "to": {"name": "DONE"}}
        ]
    }

    with patch("app.api.v1.deps.get_current_user_id", return_value=1), \
         patch("app.api.v1.deps.check_user_exists"), \
         patch("app.api.v1.controllers.jira_controller.get_jira_auth_credentials", return_value=("http://jira/rest/api/3", {})), \
         patch("app.datasources.jira_datasource.JiraDatasource.fetch_issue_transitions", new_callable=AsyncMock, return_value=valid_trans), \
         patch("app.datasources.jira_datasource.JiraDatasource.post_issue_transition", new_callable=AsyncMock):
        res = await transition_issue("K1", payload, mock_req, mock_db)
        assert res["status"] == "success"

@pytest.mark.asyncio
async def test_jira_webhook():
    mock_db = MagicMock()
    payload = JiraWebhookPayload.model_validate({
        "issue": {
            "id": "100",
            "key": "P1-100",
            "fields": {
                "summary": "Fix bug",
                "status": {"name": "Done"},
                "project": {"id": "1"},
                "created": "2026-01-01T00:00:00Z",
                "resolutiondate": "2026-01-02T00:00:00Z",
                "customfield_10028": 3
            }
        }
    })

    with patch("app.repositories.project_repo.get", return_value=MagicMock(id_proyecto="1")), \
         patch("app.repositories.issue_repo.get_by_key", return_value=None), \
         patch("app.repositories.issue_repo.create") as mock_create, \
         patch("app.api.v1.controllers.jira_controller.calculate_and_save_kpis"):
        res = await jira_webhook(payload, mock_db)
        assert res["status"] == "success"
        assert mock_create.called
