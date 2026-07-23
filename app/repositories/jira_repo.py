# app/repositories/jira_repo.py
# Módulo de repositorios para el dominio de entidades de Jira (Proyecto, Sprint, Issue, Transiciones, MapeoEstado)
# Implementa consultas especializadas y delegación de agregaciones directamente al motor SQL

from typing import Optional, Any
from sqlalchemy.orm import Session
from sqlalchemy import select, func, case
from app.models.jira import Proyecto, Sprint, Issue, TransicionEstadoIssue, MapeoEstado
from app.repositories.base import CRUDBase

class CRUDProyecto(CRUDBase[Proyecto]):
    """Repositorio especializado para operaciones sobre la entidad Proyecto."""
    
    def get_by_key(self, db: Session, key: str) -> Optional[Proyecto]:
        """Obtiene un proyecto buscando por su clave alfanumérica única (ej: 'MCHAV', 'ASD')."""
        return db.query(Proyecto).filter(Proyecto.key_proyecto == key).first()

class CRUDSprint(CRUDBase[Sprint]):
    """Repositorio especializado para operaciones sobre la entidad Sprint."""
    
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
        """Obtiene los sprints de un proyecto específico con opciones de paginación y ordenamiento."""
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

    def get_by_id_sprint(self, db: Session, sprint_id: str) -> Optional[Sprint]:
        """Obtiene un sprint buscando por su identificador único asignado por Jira."""
        return db.query(Sprint).filter(Sprint.id_sprint == sprint_id).first()

class CRUDIssue(CRUDBase[Issue]):
    """Repositorio especializado para la entidad Issue con consultas de agregación analítica de alta performance."""
    
    def get_by_project(self, db: Session, project_id: str):
        """Lista todos los tickets pertenecientes a un proyecto."""
        return db.query(Issue).filter(Issue.id_proyecto == project_id).all()
        
    def get_by_sprint(self, db: Session, sprint_id: str):
        """Lista todos los tickets pertenecientes a un sprint específico."""
        return db.query(Issue).filter(Issue.id_sprint == sprint_id).all()

    def get_by_key(self, db: Session, issue_key: str) -> Optional[Issue]:
        """Busca un ticket por su clave alfanumérica única (ej: 'MCHAV-101')."""
        return db.query(Issue).filter(Issue.key_issue == issue_key).first()

    def get_distinct_statuses_by_project(self, db: Session, project_id: str):
        """Obtiene los nombres distintos de estado actual registrados en los tickets del proyecto."""
        return db.query(Issue.status_actual).filter(Issue.id_proyecto == project_id).distinct().all()

    def get_resolved_stats_by_project(self, db: Session, project_id: str, in_progress_statuses: set[str]):
        """
        Calcula de forma agregada a nivel de base de datos (PostgreSQL o SQLite) las métricas globales del proyecto:
        - Suma total de Story Points resueltos (Velocity total)
        - Cantidad de tickets resueltos (Throughput)
        - Promedio de Lead Time en días
        - Promedio de Cycle Time en días
        Compatible con dialectos PostgreSQL (extract epoch) y SQLite (julianday).
        """
        dialect_name = db.bind.dialect.name
        
        # Subconsulta para determinar la primera fecha en que el ticket pasó a un estado "En Progreso"
        first_progress_date_sub = select(
            func.min(TransicionEstadoIssue.fecha_cambio)
        ).where(
            TransicionEstadoIssue.id_jira == Issue.id_jira,
            func.lower(TransicionEstadoIssue.estado_nuevo).in_(list(in_progress_statuses))
        ).scalar_subquery()
        
        # Expresiones matemáticas de diferencia de fechas ajustadas por motor SQL
        if dialect_name == "sqlite":
            lead_time_expr = func.julianday(Issue.resolved_at) - func.julianday(Issue.created_at)
            start_date_expr = func.coalesce(first_progress_date_sub, Issue.created_at)
            cycle_time_expr = func.julianday(Issue.resolved_at) - func.julianday(start_date_expr)
        else:
            lead_time_expr = func.extract('epoch', Issue.resolved_at - Issue.created_at) / 86400.0
            start_date_expr = func.coalesce(first_progress_date_sub, Issue.created_at)
            cycle_time_expr = func.extract('epoch', Issue.resolved_at - start_date_expr) / 86400.0
            
        # Limitar valores negativos anómalos a 0.0 mediante cláusula CASE
        lead_time_clipped = case((lead_time_expr > 0.0, lead_time_expr), else_=0.0)
        cycle_time_clipped = case((cycle_time_expr > 0.0, cycle_time_expr), else_=0.0)
        
        # Ejecutar agregaciones agrupadas
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
        """
        Calcula de forma agregada a nivel de base de datos las métricas específicas de un Sprint determinado:
        (Velocity, Throughput, Lead Time Promedio, Cycle Time Promedio).
        """
        dialect_name = db.bind.dialect.name
        
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
    """Repositorio para la gestión del historial de transiciones de estado."""
    
    def delete_by_issue(self, db: Session, issue_id: str):
        """Elimina todas las transiciones registradas para un ticket en específico."""
        db.query(TransicionEstadoIssue).filter(TransicionEstadoIssue.id_jira == issue_id).delete()
        db.commit()
        
    def get_existing(self, db: Session, issue_id: str, fecha_cambio: Any, estado_origen: Optional[str], estado_destino: str):
        """Evita duplicidad al verificar si una transición específica ya se encuentra registrada en la BD."""
        return db.query(TransicionEstadoIssue).filter(
            TransicionEstadoIssue.id_jira == issue_id,
            TransicionEstadoIssue.fecha_cambio == fecha_cambio,
            TransicionEstadoIssue.estado_anterior == estado_origen,
            TransicionEstadoIssue.estado_nuevo == estado_destino
        ).first()

    def get_distinct_new_statuses_by_project(self, db: Session, project_id: str):
        """Obtiene todos los estados de llegada (destino) registrados en las transiciones de los tickets del proyecto."""
        return db.query(TransicionEstadoIssue.estado_nuevo).join(Issue).filter(Issue.id_proyecto == project_id).distinct().all()

    def get_distinct_prev_statuses_by_project(self, db: Session, project_id: str):
        """Obtiene todos los estados de origen registrados en las transiciones de los tickets del proyecto."""
        return db.query(TransicionEstadoIssue.estado_anterior).join(Issue).filter(Issue.id_proyecto == project_id).distinct().all()

class CRUDMapeoEstado(CRUDBase[MapeoEstado]):
    """Repositorio para la gestión de las configuraciones de mapeo de estado por proyecto."""
    
    def get_by_project(self, db: Session, project_id: str):
        """Obtiene todos los mapeos configurados para un proyecto."""
        return db.query(MapeoEstado).filter(MapeoEstado.id_proyecto == project_id).all()

    def get_by_project_and_base(self, db: Session, project_id: str, base_state: str):
        """Obtiene los mapeos asociados a un estado base específico (ej: 'IN_PROGRESS')."""
        return db.query(MapeoEstado).filter(MapeoEstado.id_proyecto == project_id, MapeoEstado.estado_base == base_state).all()

    def delete_by_project(self, db: Session, project_id: str):
        """Elimina todas las reglas de mapeo asociadas a un proyecto para ser reconfiguradas."""
        db.query(MapeoEstado).filter(MapeoEstado.id_proyecto == project_id).delete()
        db.commit()

# Instancias singleton exportables de cada repositorio
project_repo = CRUDProyecto(Proyecto)
sprint_repo = CRUDSprint(Sprint)
issue_repo = CRUDIssue(Issue)
transition_repo = CRUDTransicion(TransicionEstadoIssue)
mapping_repo = CRUDMapeoEstado(MapeoEstado)
