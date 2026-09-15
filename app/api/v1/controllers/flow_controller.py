# app/api/v1/controllers/flow_controller.py

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.api.v1.deps import get_db
from app.services import flow_service
from typing import Optional

router = APIRouter()

@router.get("/cycle-time")
def get_cycle_time(
    proyecto_id: str,
    sprint_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna percentiles y métricas generales del Cycle Time para un proyecto o sprint.
    """
    return flow_service.calculate_cycle_time_percentiles(db, proyecto_id, sprint_id)

@router.get("/efficiency")
def get_flow_efficiency(
    proyecto_id: str,
    sprint_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna los porcentajes y días de Flow Efficiency (Active, Waiting, Blocked).
    """
    return flow_service.calculate_flow_efficiency(db, proyecto_id, sprint_id)

@router.get("/bottlenecks")
def get_bottlenecks(
    proyecto_id: str,
    sprint_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna métricas de tiempo por cada estado para detectar cuellos de botella.
    """
    return flow_service.detect_bottlenecks(db, proyecto_id, sprint_id)

@router.get("/blockers")
def get_blockers(
    proyecto_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna tickets actualmente bloqueados y por cuánto tiempo.
    """
    return flow_service.get_blockers(db, proyecto_id)

@router.get("/aging")
def get_aging(
    proyecto_id: str,
    db: Session = Depends(get_db)
):
    """
    Retorna tickets en progreso (Active, Waiting, Blocked) ordenados por su tiempo sin finalizar.
    """
    return flow_service.get_aging_work(db, proyecto_id)

@router.get("/cfd-wip")
def get_cfd_wip(
    proyecto_id: str,
    sprint_id: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Retorna WIP actual y evolución de estados para el Cumulative Flow Diagram.
    """
    return flow_service.calculate_cfd_and_wip(db, proyecto_id, sprint_id)
