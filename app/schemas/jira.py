from pydantic import BaseModel, Field


class JqlSearchRequest(BaseModel):
    jql: str = Field(..., min_length=3, description="Consulta JQL validada contra Jira")
    start_at: int = Field(0, ge=0)
    max_results: int = Field(50, ge=1, le=100)


class JqlSearchResponse(BaseModel):
    total: int
    start_at: int
    max_results: int
    issues: list[dict]


class SyncProjectRequest(BaseModel):
    project_key: str = Field(..., min_length=2, max_length=20)


class SyncProjectResponse(BaseModel):
    project_key: str
    issues_synced: int
    sprints_synced: int
    duration_sec: float
