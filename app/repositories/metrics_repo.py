from sqlalchemy.orm import Session
from app.models.metrics import KpisHistoricos, LogsSincronizacion
from app.repositories.base import CRUDBase

class CRUDKpi(CRUDBase[KpisHistoricos]):
    def get_general_kpi(self, db: Session, project_id: str):
        return db.query(KpisHistoricos).filter(
            KpisHistoricos.id_proyecto == project_id,
            KpisHistoricos.id_sprint == None
        ).order_by(KpisHistoricos.fecha_calculo.desc()).first()

    def get_sprint_kpi(self, db: Session, project_id: str, sprint_id: str):
        return db.query(KpisHistoricos).filter(
            KpisHistoricos.id_proyecto == project_id,
            KpisHistoricos.id_sprint == sprint_id
        ).order_by(KpisHistoricos.fecha_calculo.desc()).first()
        
    def get_all_by_project(self, db: Session, project_id: str):
        # Devuelve la consulta (Query) para ser usada con .limit() o .offset() después si se desea
        return db.query(KpisHistoricos).filter(KpisHistoricos.id_proyecto == project_id)

class CRUDLog(CRUDBase[LogsSincronizacion]):
    def get_recent(self, db: Session, *, skip: int = 0, limit: int = 20):
        return db.query(LogsSincronizacion).order_by(LogsSincronizacion.fecha_ejecucion.desc()).offset(skip).limit(limit).all()


kpi_repo = CRUDKpi(KpisHistoricos)
log_repo = CRUDLog(LogsSincronizacion)
