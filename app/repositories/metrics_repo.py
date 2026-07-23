# app/repositories/metrics_repo.py
# Repositorios especializados para el dominio de Métricas (KpisHistoricos y LogsSincronizacion)

from sqlalchemy.orm import Session
from app.models.metrics import KpisHistoricos, LogsSincronizacion
from app.repositories.base import CRUDBase

class CRUDKpi(CRUDBase[KpisHistoricos]):
    """Repositorio especializado para consultar e insertar métricas y KPIs calculados."""
    
    def get_general_kpi(self, db: Session, project_id: str):
        """Obtiene la métrica global calculada más reciente para un proyecto (donde id_sprint es None)."""
        return db.query(KpisHistoricos).filter(
            KpisHistoricos.id_proyecto == project_id,
            KpisHistoricos.id_sprint == None
        ).order_by(KpisHistoricos.fecha_calculo.desc()).first()

    def get_sprint_kpi(self, db: Session, project_id: str, sprint_id: str):
        """Obtiene el registro de KPI histórico más reciente calculado para un sprint determinado."""
        return db.query(KpisHistoricos).filter(
            KpisHistoricos.id_proyecto == project_id,
            KpisHistoricos.id_sprint == sprint_id
        ).order_by(KpisHistoricos.fecha_calculo.desc()).first()
        
    def get_all_by_project(self, db: Session, project_id: str):
        """Devuelve el objeto de consulta (Query) de todos los KPIs del proyecto para encadenar filtros, paginación u ordenamiento."""
        return db.query(KpisHistoricos).filter(KpisHistoricos.id_proyecto == project_id)

class CRUDLog(CRUDBase[LogsSincronizacion]):
    """Repositorio especializado para consultar e insertar registros de auditoría de sincronización ETL."""
    
    def get_recent(self, db: Session, *, skip: int = 0, limit: int = 20):
        """Obtiene los logs de sincronización más recientes ordenados descendentemente por fecha de ejecución."""
        return db.query(LogsSincronizacion).order_by(LogsSincronizacion.fecha_ejecucion.desc()).offset(skip).limit(limit).all()

# Instancias singleton exportables
kpi_repo = CRUDKpi(KpisHistoricos)
log_repo = CRUDLog(LogsSincronizacion)
