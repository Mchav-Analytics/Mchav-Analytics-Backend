import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from app.services.jira_sync_service import refresh_user_token, sync_projects

@pytest.mark.asyncio
async def test_refresh_user_token_no_token():
    mock_db = MagicMock()
    mock_user = MagicMock(refresh_token=None)
    mock_client = AsyncMock()
    await refresh_user_token(mock_db, mock_user, mock_client)
    assert not mock_client.post.called

@pytest.mark.asyncio
async def test_refresh_user_token_success():
    mock_db = MagicMock()
    mock_user = MagicMock(id_usuario=1, refresh_token="old_rt")
    mock_client = MagicMock()
    mock_res = MagicMock(status_code=200)
    mock_res.json.return_value = {"access_token": "new_at", "refresh_token": "new_rt"}
    mock_client.post = AsyncMock(return_value=mock_res)

    with patch("app.repositories.user_repo.update") as mock_user_update:
        await refresh_user_token(mock_db, mock_user, mock_client)
        assert mock_user_update.called

@pytest.mark.asyncio
async def test_sync_projects_create_and_update():
    mock_db = MagicMock()
    mock_user = MagicMock()
    mock_client = MagicMock()

    projects_data = [
        {"key": "P1", "name": "Proj 1", "id": "100"},
        {"key": "P2", "name": "Proj 2", "id": "200"}
    ]

    def get_by_key_handler(db, key):
        if key == "P1":
            return None # To test create
        return MagicMock(key_proyecto="P2") # To test update

    with patch("app.datasources.jira_datasource.JiraDatasource.fetch_projects", new_callable=AsyncMock, return_value=projects_data), \
         patch("app.repositories.project_repo.get_by_key", side_effect=get_by_key_handler), \
         patch("app.repositories.project_repo.create") as mock_create, \
         patch("app.repositories.project_repo.update") as mock_update:
        res = await sync_projects(mock_client, "http://jira", {}, mock_db, mock_user)
        assert len(res) == 2
        assert mock_create.called
        assert mock_update.called
