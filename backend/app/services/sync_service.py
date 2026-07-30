"""Sincronización Jira → PostgreSQL (orquesta gateway + repositorio)."""

from __future__ import annotations

import time

from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import JiraConnectionError, JiraNotFoundError
from app.datasources.jira_client import JiraClient
from app.db.unit_of_work import UnitOfWork
from app.models import Project
from app.ports.jira_gateway import JiraGateway
from app.repositories import SyncRepository
from app.services.jql_builder import JqlBuilder
from app.services.mappers.jira_mapper import (
    map_jira_board,
    map_jira_issue,
    map_jira_project,
    map_jira_sprint,
)


class SyncService:
    def __init__(self, db: Session, jira: JiraGateway | None = None):
        self.uow = UnitOfWork(db)
        self.sync = SyncRepository(db)
        self.jira = jira or JiraClient()

    def _upsert_project(self, project_key: str) -> Project:
        remote = self.jira.get_project(project_key)
        if not remote:
            raise JiraNotFoundError(f"Proyecto {project_key} no encontrado en Jira")
        return self.sync.upsert_project(map_jira_project(remote))

    def _sync_boards_and_sprints(self, project: Project) -> int:
        sprint_count = 0
        for board_data in self.jira.get_boards(project.project_key):
            board = self.sync.upsert_board(
                map_jira_board(board_data, project.id_project)
            )
            for sprint_data in self.jira.get_sprints(str(board_data.get("id"))):
                self.sync.upsert_sprint(map_jira_sprint(sprint_data, board.id_board))
                sprint_count += 1
        self.sync.commit()
        return sprint_count

    def _sync_issues(self, project: Project, max_results: int = 100) -> int:
        jql = JqlBuilder.project_issues(project.project_key)
        payload = self.jira.search_issues(jql=jql, max_results=max_results)
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
                    sprint_name = (
                        latest.split(",")[-1].strip() if "," in latest else latest
                    )

            issue_type = self.sync.get_or_create_issue_type(
                fields.get("issuetype", {}).get("name", "Task")
            )
            sprint_id = self.sync.find_sprint_id(project.project_key, sprint_name)
            mapped = map_jira_issue(issue_data, issue_type.id_type, sprint_id)
            self.sync.upsert_issue(mapped)
            synced += 1

        self.sync.commit()
        return synced

    def sync_project(self, project_key: str, max_issues: int = 100) -> dict:
        started = time.perf_counter()
        job = self.sync.get_or_create_job(
            job_name=f"sync-{project_key}", job_type="project_full"
        )

        try:
            project = self._upsert_project(project_key)
            sprints_synced = self._sync_boards_and_sprints(project)
            issues_synced = self._sync_issues(project, max_results=max_issues)
            duration = time.perf_counter() - started
            self.sync.add_log(
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
            self.sync.add_log(
                job, status="error", records_count=0, duration_sec=duration, message="Fallo sync"
            )
            raise
        except Exception as exc:
            duration = time.perf_counter() - started
            self.sync.add_log(
                job, status="error", records_count=0, duration_sec=duration, message=str(exc)
            )
            raise JiraConnectionError(
                f"Error al sincronizar proyecto {project_key}: {exc}"
            ) from exc
