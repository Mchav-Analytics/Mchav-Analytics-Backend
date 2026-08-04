# app/repositories/dev_metrics_repo.py
# Repositorio especializado para el CRUD de KPIs individuales por desarrollador

from sqlalchemy.orm import Session
from app.models.metrics import KpisDesarrollador
from app.repositories.base import CRUDBase

class CRUDKpiDesarrollador(CRUDBase[KpisDesarrollador]):
    """Repositorio para consultar e insertar métricas históricas individuales por desarrollador."""

    def get_by_dev_and_sprint(self, db: Session, project_id: str, assignee_id: str, sprint_id: str = None):
        """Obtiene la métrica calculada más reciente para un desarrollador en un sprint determinado."""
        query = db.query(KpisDesarrollador).filter(
            KpisDesarrollador.id_proyecto == project_id,
            KpisDesarrollador.assignee_id == assignee_id
        )
        if sprint_id:
            query = query.filter(KpisDesarrollador.id_sprint == sprint_id)
        else:
            query = query.filter(KpisDesarrollador.id_sprint == None)
            
        return query.order_by(KpisDesarrollador.fecha_calculo.desc()).first()

    def get_all_by_project(self, db: Session, project_id: str):
        """Obtiene todas las métricas de desarrolladores registradas para un proyecto."""
        return db.query(KpisDesarrollador).filter(KpisDesarrollador.id_proyecto == project_id).all()

dev_kpi_repo = CRUDKpiDesarrollador(KpisDesarrollador)
