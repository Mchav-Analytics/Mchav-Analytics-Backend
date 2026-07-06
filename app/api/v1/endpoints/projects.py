from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import verify_session_id
from app.services.kpi import calculate_and_save_kpis
import app.models as models

router = APIRouter()

def get_current_user_id(request: Request) -> int:
    signed_session = request.cookies.get("session_id")
    if not signed_session:
        raise HTTPException(status_code=401, detail="No autenticado")
        
    user_id = verify_session_id(signed_session)
    if not user_id:
        raise HTTPException(status_code=401, detail="Sesión inválida o expirada")
    return user_id

def check_user_exists(db: Session, user_id: int):
    user = db.query(models.User).filter(models.User.id_usuario == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="Usuario no encontrado")
    return user

@router.get("")
@router.get("/")
async def get_projects(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
    
    projects = db.query(models.Proyecto).all()
    return projects

@router.get("/{proyecto_id}/kpis")
async def get_project_kpis(proyecto_id: str, request: Request, sprint_id: str = None, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
        
    query = db.query(models.KpisHistoricos).filter(models.KpisHistoricos.id_proyecto == proyecto_id)
    if sprint_id:
        query = query.filter(models.KpisHistoricos.id_sprint == sprint_id)
        
    kpis = query.order_by(models.KpisHistoricos.fecha_calculo.asc()).all()
    return kpis

@router.get("/{proyecto_id}/sprints")
async def get_project_sprints(proyecto_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
        
    sprints = db.query(models.Sprint).filter(models.Sprint.id_proyecto == proyecto_id).all()
    return sprints

@router.get("/{proyecto_id}/statuses")
async def get_project_unique_statuses(proyecto_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
        
    statuses = db.query(models.Issue.status_actual).filter(models.Issue.id_proyecto == proyecto_id).distinct().all()
    transitions_statuses_new = db.query(models.TransicionEstadoIssue.estado_nuevo).join(models.Issue).filter(models.Issue.id_proyecto == proyecto_id).distinct().all()
    transitions_statuses_prev = db.query(models.TransicionEstadoIssue.estado_anterior).join(models.Issue).filter(models.Issue.id_proyecto == proyecto_id).distinct().all()
    
    unique_statuses = set()
    for s in statuses:
        if s[0]: unique_statuses.add(s[0])
    for s in transitions_statuses_new:
        if s[0]: unique_statuses.add(s[0])
    for s in transitions_statuses_prev:
        if s[0]: unique_statuses.add(s[0])
        
    return sorted(list(unique_statuses))

@router.get("/{proyecto_id}/mappings")
async def get_project_mappings(proyecto_id: str, request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
        
    mappings = db.query(models.MapeoEstado).filter(models.MapeoEstado.id_proyecto == proyecto_id).all()
    return mappings

@router.post("/{proyecto_id}/mappings")
async def save_project_mappings(proyecto_id: str, mappings_data: list[dict], request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)
    check_user_exists(db, user_id)
        
    db.query(models.MapeoEstado).filter(models.MapeoEstado.id_proyecto == proyecto_id).delete()
    
    for item in mappings_data:
        mapping = models.MapeoEstado(
            id_proyecto=proyecto_id,
            estado_jira=item.get("estado_jira"),
            estado_base=item.get("estado_base")
        )
        db.add(mapping)
        
    db.commit()
    
    calculate_and_save_kpis(db, proyecto_id)
    
    return {"message": "Mapeo guardado y KPIs recalculados con éxito"}
