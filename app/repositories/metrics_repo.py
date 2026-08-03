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

    def has_running_sync(self, db: Session) -> bool:
        """HU-007 CA-03: Retorna True si ya existe una sincronización en proceso ('RUNNING')."""
        count = db.query(LogsSincronizacion).filter(LogsSincronizacion.resultado == "RUNNING").count()
        return count > 0

    def get_filtered_logs(
        self, 
        db: Session, 
        *, 
        tipo_sincronizacion: str = None, 
        resultado: str = None, 
        fecha_inicio: str = None, 
        fecha_fin: str = None, 
        skip: int = 0, 
        limit: int = 20
    ):
        """HU-008 CA-03: Permite consultar y filtrar registros de auditoría por tipo de evento, resultado y fechas."""
        if not tipo_sincronizacion and not resultado and not fecha_inicio and not fecha_fin:
            return self.get_recent(db, skip=skip, limit=limit)

        query = db.query(LogsSincronizacion)

        if tipo_sincronizacion:
            query = query.filter(LogsSincronizacion.tipo_sincronizacion.ilike(f"%{tipo_sincronizacion}%"))

        if resultado:
            query = query.filter(LogsSincronizacion.resultado.ilike(f"%{resultado}%"))

        if fecha_inicio:
            try:
                from datetime import datetime
                dt_start = datetime.fromisoformat(fecha_inicio.replace("Z", "+00:00"))
                query = query.filter(LogsSincronizacion.fecha_ejecucion >= dt_start)
            except ValueError:
                pass

        if fecha_fin:
            try:
                from datetime import datetime
                dt_end = datetime.fromisoformat(fecha_fin.replace("Z", "+00:00"))
                query = query.filter(LogsSincronizacion.fecha_ejecucion <= dt_end)
            except ValueError:
                pass

        return query.order_by(LogsSincronizacion.fecha_ejecucion.desc()).offset(skip).limit(limit).all()

# Instancias singleton exportables
kpi_repo = CRUDKpi(KpisHistoricos)
log_repo = CRUDLog(LogsSincronizacion)

