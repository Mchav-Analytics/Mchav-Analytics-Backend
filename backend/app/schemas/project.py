from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProjectOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_project: int
    jira_project_id: str
    project_key: str
    project_name: str
    status: str | None
    created_at: datetime | None


class SprintOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_sprint: int
    jira_sprint_id: str
    name: str
    start_date: datetime | None
    end_date: datetime | None
    state: str
    id_board: int


class IssueOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_issue: int
    jira_issue_id: str
    issue_key: str
    summary: str
    status: str
    assignee: str | None
    story_points: int | None
    created_at: datetime
    started_at: datetime | None
    resolved_at: datetime | None
    id_sprint: int | None
