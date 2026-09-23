import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from app.datasources.jira_datasource import JiraDatasource, JiraTransientError
import httpx

@pytest.mark.asyncio
async def test_get_active_credentials():
    # 1. User with OAuth
    user_oauth = MagicMock()
    user_oauth.cloud_id = "cloud-123"
    user_oauth.access_token = "token-abc"

    mock_db = MagicMock()
    url, headers = JiraDatasource.get_auth_credentials(mock_db, user_oauth)
    assert "cloud-123" in url
    assert headers["Authorization"] == "Bearer token-abc"

    # 2. System credentials fallback (.env)
    with patch.dict("os.environ", {
        "JIRA_DOMAIN": "test.atlassian.net",
        "JIRA_EMAIL": "admin@test.com",
        "JIRA_API_TOKEN": "enc_token"
    }), patch("app.core.security.decrypt_jira_token", return_value="raw_token"):
        url2, headers2 = JiraDatasource.get_auth_credentials(mock_db, None)
        assert "https://test.atlassian.net" in url2
        assert "Basic " in headers2["Authorization"]

    # 3. No credentials -> exception
    with patch.dict("os.environ", {"JIRA_DOMAIN": "", "JIRA_EMAIL": "", "JIRA_API_TOKEN": ""}, clear=True):
        with pytest.raises(Exception, match="No hay credenciales"):
            JiraDatasource.get_auth_credentials(mock_db, None)

@pytest.mark.asyncio
async def test_get_issue_transitions_success_and_fallback():
    mock_client = AsyncMock()
    
    # Success on first attempt
    mock_resp_200 = MagicMock()
    mock_resp_200.status_code = 200
    mock_resp_200.json.return_value = {"transitions": [{"id": "31", "name": "Done"}]}
    mock_client.get.return_value = mock_resp_200

    res = await JiraDatasource.fetch_issue_transitions(mock_client, "https://api.atlassian.com", {}, "PROJ-1")
    assert len(res["transitions"]) == 1

    # Fallback from 401 to system credentials
    mock_resp_401 = MagicMock(status_code=401, text="Unauthorized")
    mock_resp_sys = MagicMock(status_code=200)
    mock_resp_sys.json.return_value = {"transitions": [{"id": "21", "name": "In Progress"}]}

    mock_client.get.side_effect = [mock_resp_401, mock_resp_sys]
    with patch.object(JiraDatasource, "get_system_credentials", return_value=("https://sys", {})):
        res2 = await JiraDatasource.fetch_issue_transitions(mock_client, "https://api.atlassian.com", {}, "PROJ-1")
        assert res2["transitions"][0]["name"] == "In Progress"

@pytest.mark.asyncio
async def test_post_issue_transition_and_assign():
    mock_client = AsyncMock()
    
    # 204 success
    mock_resp_204 = MagicMock(status_code=204)
    mock_client.post.return_value = mock_resp_204

    res = await JiraDatasource.post_issue_transition(mock_client, "https://api.atlassian.com", {}, "PROJ-1", "31")
    assert res["status"] == "success"

    # Assign issue 200 success
    mock_resp_200 = MagicMock(status_code=200)
    mock_client.put.return_value = mock_resp_200
    res_assign = await JiraDatasource.assign_issue(mock_client, "https://api.atlassian.com", {}, "PROJ-1", "acc-123")
    assert res_assign["status"] == "success"

@pytest.mark.asyncio
async def test_search_assignable_user():
    mock_client = AsyncMock()
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = [{"accountId": "acc-1", "displayName": "Developer"}]
    mock_client.get.return_value = mock_resp

    users = await JiraDatasource.search_assignable_user(mock_client, "https://api.atlassian.com", {}, "dev", "PROJ")
    assert len(users) == 1
    assert users[0]["accountId"] == "acc-1"

@pytest.mark.asyncio
async def test_fetch_projects():
    mock_client = AsyncMock()
    mock_resp = MagicMock(status_code=200)
    mock_resp.json.return_value = [{"id": "1000", "key": "PROJ"}]
    mock_client.get.return_value = mock_resp

    projects = await JiraDatasource.fetch_projects(mock_client, "https://api", {})
    assert len(projects) == 1

@pytest.mark.asyncio
async def test_search_issues_jql_all_branches():
    mock_client = AsyncMock()

    # 1. Success POST with nextPageToken
    resp_post = MagicMock(status_code=200)
    resp_post.json.return_value = {"issues": [{"key": "ISSUE-1"}], "nextPageToken": "token-xyz"}
    mock_client.post.return_value = resp_post

    res = await JiraDatasource.fetch_issues_jql(mock_client, "https://api", {}, "project = TEST", next_page_token="tok1")
    assert len(res["issues"]) == 1

    # 2. 429 Rate limiting
    mock_client.post.return_value = MagicMock(status_code=429)
    with pytest.raises(JiraTransientError):
        await JiraDatasource.fetch_issues_jql(mock_client, "https://api", {}, "project = TEST")

    # 3. Fallback to GET /search legacy
    mock_client.post.return_value = MagicMock(status_code=400, text="New API not supported")
    resp_legacy = MagicMock(status_code=200)
    resp_legacy.json.return_value = {"issues": [{"key": "LEGACY-1"}]}
    mock_client.get.return_value = resp_legacy

    res_legacy = await JiraDatasource.fetch_issues_jql(mock_client, "https://api", {}, "project = TEST")
    assert res_legacy["issues"][0]["key"] == "LEGACY-1"

    # 4. Both fail -> exception
    mock_client.get.return_value = MagicMock(status_code=500, text="Internal Error")
    with pytest.raises(Exception, match="Error al buscar issues"):
        await JiraDatasource.fetch_issues_jql(mock_client, "https://api", {}, "project = TEST")

@pytest.mark.asyncio
async def test_fetch_issue_changelog_and_boards():
    mock_client = AsyncMock()

    # 1. Changelog 200
    mock_client.get.return_value = MagicMock(status_code=200, json=lambda: {"values": [{"id": "1"}]})
    res = await JiraDatasource.fetch_issue_changelog(mock_client, "https://api", {}, "1001")
    assert len(res["values"]) == 1

    # Changelog 404 returns {"values": []}
    mock_client.get.return_value = MagicMock(status_code=404)
    res_empty = await JiraDatasource.fetch_issue_changelog(mock_client, "https://api", {}, "1001")
    assert res_empty["values"] == []

    # 2. Boards 200
    mock_client.get.return_value = MagicMock(status_code=200, json=lambda: {"values": [{"id": 10, "name": "Board"}]})
    boards = await JiraDatasource.fetch_boards_for_project(mock_client, "https://api/agile/1.0", {}, "PROJ")
    assert len(boards["values"]) == 1

    # Boards 500 returns empty
    mock_client.get.return_value = MagicMock(status_code=500)
    boards_empty = await JiraDatasource.fetch_boards_for_project(mock_client, "https://api/agile/1.0", {}, "PROJ")
    assert boards_empty["values"] == []

    # 3. Board Sprints 200
    mock_client.get.return_value = MagicMock(status_code=200, json=lambda: {"values": [{"id": 100, "name": "Sprint 1"}]})
    sprints = await JiraDatasource.fetch_board_sprints(mock_client, "https://api/agile/1.0", {}, 10)
    assert len(sprints["values"]) == 1

    # Board Sprints 404 returns empty
    mock_client.get.return_value = MagicMock(status_code=404)
    sprints_empty = await JiraDatasource.fetch_board_sprints(mock_client, "https://api/agile/1.0", {}, 10)
    assert sprints_empty["values"] == []

@pytest.mark.asyncio
async def test_fetch_issue_details_and_transition_fallbacks():
    mock_client = AsyncMock()

    # 1. fetch_issue_details 200
    mock_client.get.return_value = MagicMock(status_code=200, json=lambda: {"fields": {"summary": "Detail"}})
    res = await JiraDatasource.fetch_issue_details(mock_client, "https://api", {}, "PROJ-1")
    assert res["fields"]["summary"] == "Detail"

    # fetch_issue_details 401 with system fallback
    resp_401 = MagicMock(status_code=401)
    resp_sys = MagicMock(status_code=200, json=lambda: {"fields": {"summary": "Sys Detail"}})
    mock_client.get.side_effect = [resp_401, resp_sys]

    with patch.object(JiraDatasource, "get_system_credentials", return_value=("https://sys", {})):
        res_sys_detail = await JiraDatasource.fetch_issue_details(mock_client, "https://api", {}, "PROJ-1")
        assert res_sys_detail["fields"]["summary"] == "Sys Detail"

    # 2. post_issue_transition 401 scope error fallback
    resp_scope = MagicMock(status_code=403, text="Scope does not match")
    resp_post_sys = MagicMock(status_code=204)
    mock_client.post.side_effect = [resp_scope, resp_post_sys]

    with patch.object(JiraDatasource, "get_system_credentials", return_value=("https://sys", {})):
        res_trans = await JiraDatasource.post_issue_transition(mock_client, "https://api", {}, "PROJ-1", "31")
        assert res_trans["status"] == "success"

    # 3. assign_issue 403 scope error fallback
    resp_assign_scope = MagicMock(status_code=403, text="Scope unauthorized")
    resp_assign_sys = MagicMock(status_code=204)
    mock_client.put.side_effect = [resp_assign_scope, resp_assign_sys]

    with patch.object(JiraDatasource, "get_system_credentials", return_value=("https://sys", {})):
        res_assign = await JiraDatasource.assign_issue(mock_client, "https://api", {}, "PROJ-1", "acc-new")
        assert res_assign["status"] == "success"
