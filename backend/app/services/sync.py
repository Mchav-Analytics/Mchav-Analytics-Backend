"""Servicios de sincronización: Jira API -> PostgreSQL."""

from __future__ import annotations

import time
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import JiraConnectionError, JiraNotFoundError
from app.features.jira.models import (
    Board,
    Issue,
    IssueType,
    Project,
    Sprint,
    SyncJob,
    SyncLog,
)
from app.services.jira import JiraService
from app.services.jira_queries import project_issues_jql
from app.services.mappers.jira_mapper import (
    map_jira_board,
    map_jira_issue,
    map_jira_project,
    map_jira_sprint,
)


class SyncService:
    def __init__(self, db: Session, jira: JiraService | None = None):
        self.db = db
        self.jira = jira or JiraService()

    def _get_or_create_job(self, job_name: str, job_type: str) -> SyncJob:
        job = self.db.query(SyncJob).filter(SyncJob.job_name == job_name).first()
        if job:
            return job
        job = SyncJob(job_name=job_name, job_type=job_type, frequency="manual", is_active=True)
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def _log_execution(
        self,
        job: SyncJob,
        status: str,
        records_count: int,
        duration_sec: float,
        message: str | None = None,
    ) -> None:
        log = SyncLog(
            id_job=job.id_job,
            status=status,
            duration_sec=int(duration_sec),
            records_count=records_count,
            message=message,
            execution_date=datetime.now(timezone.utc),
        )
        self.db.add(log)
        self.db.commit()

    def _get_or_create_issue_type(self, name: str) -> IssueType:
        issue_type = self.db.query(IssueType).filter(IssueType.name == name).first()
        if issue_type:
            return issue_type
        issue_type = IssueType(name=name)
        self.db.add(issue_type)
        self.db.commit()
        self.db.refresh(issue_type)
        return issue_type

    def _upsert_project(self, project_key: str) -> Project:
        remote = self.jira.verificar_proyecto(project_key)
        if not remote:
            raise JiraNotFoundError(f"Proyecto {project_key} no encontrado en Jira")

        mapped = map_jira_project(remote)
        project = (
            self.db.query(Project)
            .filter(Project.project_key == mapped["project_key"])
            .first()
        )
        if project:
            project.project_name = mapped["project_name"]
            project.status = mapped["status"]
        else:
            project = Project(**mapped)
            self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def _sync_boards_and_sprints(self, project: Project) -> int:
        boards_payload = self.jira.obtener_boards(project.project_key)
        sprint_count = 0

        for board_data in boards_payload:
            mapped_board = map_jira_board(board_data, project.id_project)
            board = (
                self.db.query(Board)
                .filter(Board.jira_board_id == mapped_board["jira_board_id"])
                .first()
            )
            if board:
                board.name = mapped_board["name"]
                board.type = mapped_board["type"]
            else:
                board = Board(**mapped_board)
                self.db.add(board)
            self.db.commit()
            self.db.refresh(board)

            for sprint_data in self.jira.obtener_sprints(str(board_data.get("id"))):
                mapped_sprint = map_jira_sprint(sprint_data, board.id_board)
                sprint = (
                    self.db.query(Sprint)
                    .filter(Sprint.jira_sprint_id == mapped_sprint["jira_sprint_id"])
                    .first()
                )
                if sprint:
                    sprint.name = mapped_sprint["name"]
                    sprint.state = mapped_sprint["state"]
                    sprint.start_date = mapped_sprint["start_date"]
                    sprint.end_date = mapped_sprint["end_date"]
                else:
                    sprint = Sprint(**mapped_sprint)
                    self.db.add(sprint)
                sprint_count += 1

        self.db.commit()
        return sprint_count

    def _resolve_sprint_id(self, project_key: str, sprint_name: str | None) -> int | None:
        if not sprint_name:
            return None
        sprint = (
            self.db.query(Sprint)
            .join(Board, Sprint.id_board == Board.id_board)
            .join(Project, Board.id_project == Project.id_project)
            .filter(Project.project_key == project_key, Sprint.name == sprint_name)
            .first()
        )
        return sprint.id_sprint if sprint else None

    def _sync_issues(self, project: Project, max_results: int = 100) -> int:
        jql = project_issues_jql(project.project_key)
        payload = self.jira.buscar_issues(jql=jql, max_results=max_results)
        issues = payload.get("issues", [])
        synced = 0

        for issue_data in issues:
            fields = issue_data.get("fields", {})
            sprint_field = fields.get(settings.JIRA_SPRINT_FIELD) or []
            sprint_name = None
            if isinstance(sprint_field, list) and sprint_field:
                latest = sprint_field[-1]
                if isinstance(latest, dict):
                    sprint_name = latest.get("name")
                elif isinstance(latest, str):
                    sprint_name = latest.split(",")[-1].strip() if "," in latest else latest

            issue_type = self._get_or_create_issue_type(
                fields.get("issuetype", {}).get("name", "Task")
            )
            sprint_id = self._resolve_sprint_id(project.project_key, sprint_name)
            mapped = map_jira_issue(issue_data, issue_type.id_type, sprint_id)

            issue = (
                self.db.query(Issue)
                .filter(Issue.jira_issue_id == mapped["jira_issue_id"])
                .first()
            )
            payload_issue = {k: v for k, v in mapped.items() if k != "issue_type_name"}
            if issue:
                for key, value in payload_issue.items():
                    setattr(issue, key, value)
            else:
                issue = Issue(**payload_issue)
                self.db.add(issue)
            synced += 1

        self.db.commit()
        return synced

    def sync_project(self, project_key: str, max_issues: int = 100) -> dict:
        started = time.perf_counter()
        job = self._get_or_create_job(job_name=f"sync-{project_key}", job_type="project_full")

        try:
            project = self._upsert_project(project_key)
            sprints_synced = self._sync_boards_and_sprints(project)
            issues_synced = self._sync_issues(project, max_results=max_issues)
            duration = time.perf_counter() - started
            self._log_execution(
                job,
                status="success",
                records_count=issues_synced + sprints_synced,
                duration_sec=duration,
                message=f"Proyecto {project_key} sincronizado",
            )
            return {
                "project_key": project_key,
                "issues_synced": issues_synced,
                "sprints_synced": sprints_synced,
                "duration_sec": round(duration, 2),
            }
        except (JiraNotFoundError, JiraConnectionError):
            duration = time.perf_counter() - started
            self._log_execution(job, status="error", records_count=0, duration_sec=duration, message="Fallo sync")
            raise
        except Exception as exc:
            duration = time.perf_counter() - started
            self._log_execution(job, status="error", records_count=0, duration_sec=duration, message=str(exc))
            raise JiraConnectionError(f"Error al sincronizar proyecto {project_key}: {exc}") from exc
