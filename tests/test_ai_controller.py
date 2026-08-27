import pytest
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from app.api.v1.controllers.ai_controller import (
    _build_rich_project_context,
    chat_with_ai,
    get_suggested_prompts,
    ChatMessageRequest
)
import app.models as models

def test_build_rich_project_context():
    mock_db = MagicMock()
    proj = MagicMock(id_proyecto="10001", key_proyecto="P1")
    
    issue_done = MagicMock(
        id_jira="J1", key_issue="K1", summary="S1", status_actual="Done", story_points=3,
        issue_type="Story", priority="Medium", assignee_name="Dev 1", assignee_email="dev1@test.com"
    )
    issue_stuck = MagicMock(
        id_jira="J2", key_issue="K2", summary="S2", status_actual="Blocked", story_points=5,
        issue_type="Bug", priority="High", assignee_name="Dev 2", assignee_email="dev2@test.com"
    )
    
    def query_handler(model):
        m = MagicMock()
        if model == models.Proyecto:
            m.filter.return_value.first.return_value = proj
        elif model == models.Issue:
            m.filter.return_value.all.return_value = [issue_done, issue_stuck]
        elif model == models.Alert:
            m.order_by.return_value.limit.return_value.all.return_value = []
        return m

    mock_db.query.side_effect = query_handler
    
    with patch("app.api.v1.controllers.ai_controller.calculate_sprint_health", return_value={"health_score": 90}), \
         patch("app.api.v1.controllers.ai_controller.get_base_status", side_effect=["DONE", "IN_PROGRESS"]), \
         patch("app.api.v1.controllers.ai_controller.get_issue_cycle_time_days", return_value=1.5):
        ctx = _build_rich_project_context(mock_db, "P1", "User 1")
        
    assert ctx["id_proyecto"] == "10001"
    assert len(ctx["desempeno_desarrolladores_individual"]) == 2
    assert len(ctx["tickets_bloqueados_o_criticos"]) == 1

def test_chat_with_ai():
    mock_db = MagicMock()
    user = MagicMock(nombre="Mike", email="mike@test.com")
    req = ChatMessageRequest(message="Hola", project_id="P1", history=[])

    with patch("app.api.v1.controllers.ai_controller._build_rich_project_context", return_value={}), \
         patch("app.api.v1.controllers.ai_controller.chat_with_gemini", return_value="Hola desde IA"):
        res = chat_with_ai(req, db=mock_db, current_user=user)
        assert res["reply"] == "Hola desde IA"
        assert res["status"] == "success"

def test_get_suggested_prompts():
    prompts = get_suggested_prompts()
    assert len(prompts) == 4
    assert prompts[0]["category"] == "Desarrolladores"
