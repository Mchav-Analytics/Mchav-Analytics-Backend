from app.services.jql_builder import JqlBuilder
from app.services.mappers.jira_mapper import extract_story_points, map_jira_project


def test_project_issues_jql_contains_key():
    jql = JqlBuilder.project_issues("SCRUM")
    assert 'project = "SCRUM"' in jql


def test_open_issues_jql_is_unresolved():
    jql = JqlBuilder.open_issues("MCHAV")
    assert "resolution = Unresolved" in jql


def test_resolved_in_period_jql_uses_days():
    jql = JqlBuilder.resolved_in_period("MCHAV", days=14)
    assert "resolved >= -14d" in jql


def test_map_jira_project():
    payload = {"id": "10001", "key": "SCRUM", "name": "Scrum Project"}
    mapped = map_jira_project(payload)
    assert mapped["project_key"] == "SCRUM"
    assert mapped["project_name"] == "Scrum Project"


def test_extract_story_points_from_custom_field():
    fields = {"customfield_10016": 5}
    assert extract_story_points(fields) == 5


def test_extract_story_points_returns_none_when_missing():
    assert extract_story_points({}) is None
