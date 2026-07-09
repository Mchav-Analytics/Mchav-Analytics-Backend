import pytest

from app.services.jira_queries import open_issues_jql, project_issues_jql, resolved_in_period_jql
from app.services.mappers.jira_mapper import extract_story_points, map_jira_project


def test_project_issues_jql_contains_key():
    jql = project_issues_jql("SCRUM")
    assert 'project = "SCRUM"' in jql


def test_open_issues_jql_is_unresolved():
    jql = open_issues_jql("MCHAV")
    assert "resolution = Unresolved" in jql


def test_resolved_in_period_jql_uses_days():
    jql = resolved_in_period_jql("MCHAV", days=14)
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
