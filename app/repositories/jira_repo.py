from typing import Optional
from sqlalchemy.orm import Session
from app.models.jira import Proyecto, Sprint, Issue, TransicionEstadoIssue, MapeoEstado
from app.repositories.base import CRUDBase

class CRUDProyecto(CRUDBase[Proyecto]):
    pass

class CRUDSprint(CRUDBase[Sprint]):
    def get_by_project(
        self,
        db: Session,
        project_id: str,
        *,
        skip: int = 0,
        limit: Optional[int] = None,
        sort: Optional[str] = None,
        order: str = "asc"
    ):
        query = db.query(Sprint).filter(Sprint.id_proyecto == project_id)
        if sort and hasattr(Sprint, sort):
            field = getattr(Sprint, sort)
            if order.lower() == "desc":
                query = query.order_by(field.desc())
            else:
                query = query.order_by(field.asc())
        query = query.offset(skip)
        if limit is not None:
            query = query.limit(limit)
        return query.all()


class CRUDIssue(CRUDBase[Issue]):
    def get_by_project(self, db: Session, project_id: str):
        return db.query(Issue).filter(Issue.id_proyecto == project_id).all()
        
    def get_by_sprint(self, db: Session, sprint_id: str):
        return db.query(Issue).filter(Issue.id_sprint == sprint_id).all()

    def get_distinct_statuses_by_project(self, db: Session, project_id: str):
        return db.query(Issue.status_actual).filter(Issue.id_proyecto == project_id).distinct().all()

    def get_resolved_stats_by_project(self, db: Session, project_id: str, in_progress_statuses: set[str]):
        dialect_name = db.bind.dialect.name
        
        from sqlalchemy import select, func, case
        from app.models.jira import TransicionEstadoIssue
        
        first_progress_date_sub = select(
            func.min(TransicionEstadoIssue.fecha_cambio)
        ).where(
            TransicionEstadoIssue.id_jira == Issue.id_jira,
            func.lower(TransicionEstadoIssue.estado_nuevo).in_(list(in_progress_statuses))
        ).scalar_subquery()
        
        if dialect_name == "sqlite":
            lead_time_expr = func.julianday(Issue.resolved_at) - func.julianday(Issue.created_at)
            start_date_expr = func.coalesce(first_progress_date_sub, Issue.created_at)
            cycle_time_expr = func.julianday(Issue.resolved_at) - func.julianday(start_date_expr)
        else:
            lead_time_expr = func.extract('epoch', Issue.resolved_at - Issue.created_at) / 86400.0
            start_date_expr = func.coalesce(first_progress_date_sub, Issue.created_at)
            cycle_time_expr = func.extract('epoch', Issue.resolved_at - start_date_expr) / 86400.0
            
        lead_time_clipped = case((lead_time_expr > 0.0, lead_time_expr), else_=0.0)
        cycle_time_clipped = case((cycle_time_expr > 0.0, cycle_time_expr), else_=0.0)
        
        return db.query(
            func.coalesce(func.sum(Issue.story_points), 0.0),
            func.count(Issue.id_jira),
            func.coalesce(func.avg(lead_time_clipped), 0.0),
            func.coalesce(func.avg(cycle_time_clipped), 0.0)
        ).filter(
            Issue.id_proyecto == project_id,
            Issue.resolved_at.isnot(None)
        ).first()

    def get_resolved_stats_by_sprint(self, db: Session, sprint_id: str, in_progress_statuses: set[str]):
        dialect_name = db.bind.dialect.name
        
        from sqlalchemy import select, func, case
        from app.models.jira import TransicionEstadoIssue
        
        first_progress_date_sub = select(
            func.min(TransicionEstadoIssue.fecha_cambio)
        ).where(
            TransicionEstadoIssue.id_jira == Issue.id_jira,
            func.lower(TransicionEstadoIssue.estado_nuevo).in_(list(in_progress_statuses))
        ).scalar_subquery()
        
        if dialect_name == "sqlite":
            lead_time_expr = func.julianday(Issue.resolved_at) - func.julianday(Issue.created_at)
            start_date_expr = func.coalesce(first_progress_date_sub, Issue.created_at)
            cycle_time_expr = func.julianday(Issue.resolved_at) - func.julianday(start_date_expr)
        else:
            lead_time_expr = func.extract('epoch', Issue.resolved_at - Issue.created_at) / 86400.0
            start_date_expr = func.coalesce(first_progress_date_sub, Issue.created_at)
            cycle_time_expr = func.extract('epoch', Issue.resolved_at - start_date_expr) / 86400.0
            
        lead_time_clipped = case((lead_time_expr > 0.0, lead_time_expr), else_=0.0)
        cycle_time_clipped = case((cycle_time_expr > 0.0, cycle_time_expr), else_=0.0)
        
        return db.query(
            func.coalesce(func.sum(Issue.story_points), 0.0),
            func.count(Issue.id_jira),
            func.coalesce(func.avg(lead_time_clipped), 0.0),
            func.coalesce(func.avg(cycle_time_clipped), 0.0)
        ).filter(
            Issue.id_sprint == sprint_id,
            Issue.resolved_at.isnot(None)
        ).first()


class CRUDTransicion(CRUDBase[TransicionEstadoIssue]):
    def delete_by_issue(self, db: Session, issue_id: str):
        db.query(TransicionEstadoIssue).filter(TransicionEstadoIssue.id_jira == issue_id).delete()
        db.commit()
        
    def get_distinct_new_statuses_by_project(self, db: Session, project_id: str):
        return db.query(TransicionEstadoIssue.estado_nuevo).join(Issue).filter(Issue.id_proyecto == project_id).distinct().all()

    def get_distinct_prev_statuses_by_project(self, db: Session, project_id: str):
        return db.query(TransicionEstadoIssue.estado_anterior).join(Issue).filter(Issue.id_proyecto == project_id).distinct().all()

class CRUDMapeoEstado(CRUDBase[MapeoEstado]):
    def get_by_project(self, db: Session, project_id: str):
        return db.query(MapeoEstado).filter(MapeoEstado.id_proyecto == project_id).all()

    def get_by_project_and_base(self, db: Session, project_id: str, base_state: str):
        return db.query(MapeoEstado).filter(MapeoEstado.id_proyecto == project_id, MapeoEstado.estado_base == base_state).all()

    def delete_by_project(self, db: Session, project_id: str):
        db.query(MapeoEstado).filter(MapeoEstado.id_proyecto == project_id).delete()
        db.commit()

project_repo = CRUDProyecto(Proyecto)
sprint_repo = CRUDSprint(Sprint)
issue_repo = CRUDIssue(Issue)
transition_repo = CRUDTransicion(TransicionEstadoIssue)
mapping_repo = CRUDMapeoEstado(MapeoEstado)
