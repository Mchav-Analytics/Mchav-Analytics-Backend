from datetime import datetime, timezone

from app.core.config import settings


def parse_jira_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def extract_story_points(fields: dict) -> int | None:
    for field_name in settings.story_point_field_names:
        raw = fields.get(field_name)
        if raw is None:
            continue
        try:
            return int(float(raw))
        except (TypeError, ValueError):
            continue
    return None


def map_jira_project(payload: dict) -> dict:
    return {
        "jira_project_id": str(payload.get("id")),
        "project_key": payload.get("key", ""),
        "project_name": payload.get("name", ""),
        "status": "active",
    }


def map_jira_board(payload: dict, project_id: int) -> dict:
    return {
        "jira_board_id": str(payload.get("id")),
        "name": payload.get("name", ""),
        "type": payload.get("type"),
        "id_project": project_id,
    }


def map_jira_sprint(payload: dict, board_id: int) -> dict:
    return {
        "jira_sprint_id": str(payload.get("id")),
        "name": payload.get("name", ""),
        "start_date": parse_jira_datetime(payload.get("startDate")),
        "end_date": parse_jira_datetime(payload.get("endDate")),
        "state": payload.get("state", "future"),
        "id_board": board_id,
    }


def map_jira_issue(issue_payload: dict, issue_type_id: int, sprint_id: int | None) -> dict:
    fields = issue_payload.get("fields", {})
    status = fields.get("status", {})
    assignee = fields.get("assignee") or {}
    issue_type = fields.get("issuetype", {})

    return {
        "jira_issue_id": str(issue_payload.get("id")),
        "issue_key": issue_payload.get("key", ""),
        "summary": fields.get("summary", ""),
        "status": status.get("name", "Unknown"),
        "assignee": assignee.get("displayName"),
        "story_points": extract_story_points(fields),
        "created_at": parse_jira_datetime(fields.get("created")) or datetime.now(timezone.utc),
        "started_at": parse_jira_datetime(fields.get("statuscategorychangedate")),
        "resolved_at": parse_jira_datetime(fields.get("resolutiondate")),
        "id_type": issue_type_id,
        "id_sprint": sprint_id,
        "issue_type_name": issue_type.get("name", "Task"),
    }
