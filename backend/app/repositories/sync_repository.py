"""Persistencia usada por SyncService (jobs, logs, upsert Jira → local)."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Board, Issue, IssueType, Project, Sprint, SyncJob, SyncLog


class SyncRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_or_create_job(self, job_name: str, job_type: str) -> SyncJob:
        job = self.db.query(SyncJob).filter(SyncJob.job_name == job_name).first()
        if job:
            return job
        job = SyncJob(
            job_name=job_name,
            job_type=job_type,
            frequency="manual",
            is_active=True,
        )
        self.db.add(job)
        self.db.commit()
        self.db.refresh(job)
        return job

    def add_log(
        self,
        job: SyncJob,
        status: str,
        records_count: int,
        duration_sec: float,
        message: str | None = None,
    ) -> SyncLog:
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
        return log

    def get_or_create_issue_type(self, name: str) -> IssueType:
        issue_type = self.db.query(IssueType).filter(IssueType.name == name).first()
        if issue_type:
            return issue_type
        issue_type = IssueType(name=name)
        self.db.add(issue_type)
        self.db.commit()
        self.db.refresh(issue_type)
        return issue_type

    def get_project_by_key(self, project_key: str) -> Project | None:
        return (
            self.db.query(Project)
            .filter(Project.project_key == project_key)
            .first()
        )

    def upsert_project(self, mapped: dict) -> Project:
        project = self.get_project_by_key(mapped["project_key"])
        if project:
            project.project_name = mapped["project_name"]
            project.status = mapped["status"]
        else:
            project = Project(**mapped)
            self.db.add(project)
        self.db.commit()
        self.db.refresh(project)
        return project

    def get_board_by_jira_id(self, jira_board_id: str) -> Board | None:
        return (
            self.db.query(Board)
            .filter(Board.jira_board_id == jira_board_id)
            .first()
        )

    def upsert_board(self, mapped: dict) -> Board:
        board = self.get_board_by_jira_id(mapped["jira_board_id"])
        if board:
            board.name = mapped["name"]
            board.type = mapped["type"]
        else:
            board = Board(**mapped)
            self.db.add(board)
        self.db.commit()
        self.db.refresh(board)
        return board

    def get_sprint_by_jira_id(self, jira_sprint_id: str) -> Sprint | None:
        return (
            self.db.query(Sprint)
            .filter(Sprint.jira_sprint_id == jira_sprint_id)
            .first()
        )

    def upsert_sprint(self, mapped: dict) -> Sprint:
        sprint = self.get_sprint_by_jira_id(mapped["jira_sprint_id"])
        if sprint:
            sprint.name = mapped["name"]
            sprint.state = mapped["state"]
            sprint.start_date = mapped["start_date"]
            sprint.end_date = mapped["end_date"]
        else:
            sprint = Sprint(**mapped)
            self.db.add(sprint)
        return sprint

    def commit(self) -> None:
        self.db.commit()

    def find_sprint_id(
        self, project_key: str, sprint_name: str | None
    ) -> int | None:
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

    def get_issue_by_jira_id(self, jira_issue_id: str) -> Issue | None:
        return (
            self.db.query(Issue)
            .filter(Issue.jira_issue_id == jira_issue_id)
            .first()
        )

    def upsert_issue(self, mapped: dict) -> Issue:
        payload = {k: v for k, v in mapped.items() if k != "issue_type_name"}
        issue = self.get_issue_by_jira_id(payload["jira_issue_id"])
        if issue:
            for key, value in payload.items():
                setattr(issue, key, value)
        else:
            issue = Issue(**payload)
            self.db.add(issue)
        return issue
