# app/api/v1/controllers/alerts_controller.py
# Controlador HTTP para Alertas del Sistema y Solicitudes de Ayuda (Fase 8)

from typing import Optional, Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.services.alerts_engine_service import (
    get_system_alerts,
    acknowledge_alert,
    get_help_requests,
    create_help_request,
    update_help_request_status
)

router = APIRouter()

@router.get("", response_model=List[Dict[str, Any]])
@router.get("/", response_model=List[Dict[str, Any]])
async def list_system_alerts(
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto"),
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/alerts
    Obtiene la lista de alertas generadas automáticamente por el motor analítico (Bloqueos >48h, WIP excesivo, Cycle time).
    """
    try:
        return get_system_alerts(db, proyecto_id)
    except Exception as e:
        if db:
            db.rollback()
        print("Error en list_system_alerts:", e)
        return get_system_alerts(None, proyecto_id)

@router.post("/{alert_id}/acknowledge")
async def mark_alert_acknowledged(
    alert_id: int,
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/alerts/{alert_id}/acknowledge
    Marca una alerta como atendida.
    """
    try:
        return acknowledge_alert(db, alert_id)
    except Exception as e:
        if db:
            db.rollback()
        return acknowledge_alert(None, alert_id)

@router.get("/help-requests")
async def list_help_requests(
    proyecto_id: str = Query("PROJ-01", description="ID del proyecto"),
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/alerts/help-requests
    Obtiene el listado de solicitudes de ayuda y escalamiento enviadas por desarrolladores o líderes técnicos.
    """
    try:
        return get_help_requests(db, proyecto_id)
    except Exception as e:
        if db:
            db.rollback()
        return get_help_requests(None, proyecto_id)

@router.post("/help-requests")
async def submit_help_request(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db)
):
    """
    POST /api/v1/alerts/help-requests
    Permite a desarrolladores o líderes técnicos enviar una solicitud de ayuda/escalamiento.
    """
    try:
        return create_help_request(db, payload)
    except Exception as e:
        if db:
            db.rollback()
        return create_help_request(None, payload)

@router.patch("/help-requests/{request_id}")
async def update_help_status(
    request_id: int,
    status: str = Query(..., description="Nuevo estado ('PENDIENTE', 'EN_ATENCION', 'RESUELTA')"),
    responded_by: Optional[str] = Query(None, description="Nombre de quien atiende"),
    db: Session = Depends(get_db)
):
    """
    PATCH /api/v1/alerts/help-requests/{request_id}
    Actualiza el estado de una solicitud de ayuda.
    """
    try:
        return update_help_request_status(db, request_id, status, responded_by)
    except Exception as e:
        if db:
            db.rollback()
        return update_help_request_status(None, request_id, status, responded_by)
