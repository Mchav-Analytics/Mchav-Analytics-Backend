# app/api/v1/controllers/users_controller.py
# Controlador HTTP para la Gestión de Usuarios, Roles (RBAC) y Asignación de Proyectos (HU-003, HU-004, HU-005)

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Security, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import User, Role, UserProject
from app.models.jira import Proyecto

router = APIRouter()

# Esquemas Pydantic para peticiones y respuestas
class UserStatusPayload(BaseModel):
    activo: bool

class UserRolePayload(BaseModel):
    id_rol: int

class UserProjectsPayload(BaseModel):
    id_proyectos: List[str]

class RoleResponse(BaseModel):
    id_rol: int
    nombre_rol: str
    scopes: str

    class Config:
        from_attributes = True

class UserDetailResponse(BaseModel):
    id_usuario: int
    email: Optional[str]
    nombre: Optional[str]
    id_rol: Optional[int]
    rol: Optional[str]
    activo: bool
    proyectos_asignados: List[str]

    class Config:
        from_attributes = True

def _verify_admin(user: User):
    """Auxiliar para garantizar que el usuario solicitante posea el rol de Administrador."""
    rol_nombre = user.rol.nombre_rol.lower() if user.rol else ""
    if rol_nombre != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operación permitida únicamente para administradores del sistema."
        )

@router.get(
    "",
    response_model=List[UserDetailResponse],
    summary="Listar usuarios del sistema (HU-003)",
    description="Devuelve el listado completo de usuarios registrados con sus roles, estados y proyectos asignados."
)
@router.get("/", response_model=List[UserDetailResponse])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user, scopes=["jira:read"])
):
    _verify_admin(current_user)
    users = db.query(User).all()
    result = []
    for u in users:
        proj_ids = [p.id_proyecto for p in u.proyectos_asignados]
        rol_nombre = u.rol.nombre_rol if u.rol else "Sin Rol"
        result.append({
            "id_usuario": u.id_usuario,
            "email": u.email,
            "nombre": u.nombre,
            "id_rol": u.id_rol,
            "rol": rol_nombre,
            "activo": u.activo,
            "proyectos_asignados": proj_ids
        })
    return result

@router.get(
    "/roles",
    response_model=List[RoleResponse],
    summary="Listar roles disponibles",
    description="Obtiene el catálogo de roles y permisos configurados en la plataforma."
)
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user, scopes=["jira:read"])
):
    roles = db.query(Role).all()
    return roles

@router.put(
    "/{id_usuario}/status",
    summary="Activar o Desactivar usuario (HU-003 CA-01, CA-04)",
    description="Permite habilitar o deshabilitar el acceso de un usuario. El administrador no puede desactivarse a sí mismo."
)
async def update_user_status(
    id_usuario: int,
    payload: UserStatusPayload,
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user, scopes=["admin"])
):
    _verify_admin(current_user)
    
    # HU-003 CA-04: El administrador no puede desactivar su propia cuenta
    if id_usuario == current_user.id_usuario and not payload.activo:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El administrador no puede desactivar su propia cuenta."
        )

    target_user = db.query(User).filter(User.id_usuario == id_usuario).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    target_user.activo = payload.activo
    db.commit()
    db.refresh(target_user)

    estado_str = "activado" if target_user.activo else "desactivado"
    return {
        "status": "success",
        "message": f"Usuario {target_user.email} {estado_str} con éxito.",
        "id_usuario": target_user.id_usuario,
        "activo": target_user.activo
    }

@router.put(
    "/{id_usuario}/role",
    summary="Asignar rol a usuario (HU-004 CA-01, CA-02)",
    description="Actualiza el rol del usuario asignándole un único rol activo."
)
async def update_user_role(
    id_usuario: int,
    payload: UserRolePayload,
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user, scopes=["admin"])
):
    _verify_admin(current_user)

    target_user = db.query(User).filter(User.id_usuario == id_usuario).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    role = db.query(Role).filter(Role.id_rol == payload.id_rol).first()
    if not role:
        raise HTTPException(status_code=400, detail="El rol especificado no existe.")

    target_user.id_rol = role.id_rol
    db.commit()
    db.refresh(target_user)

    return {
        "status": "success",
        "message": f"Rol '{role.nombre_rol}' asignado con éxito a {target_user.email}.",
        "id_usuario": target_user.id_usuario,
        "id_rol": role.id_rol,
        "rol": role.nombre_rol
    }

@router.get(
    "/{id_usuario}/projects",
    summary="Obtener proyectos vinculados a usuario (HU-005 CA-02)",
    description="Retorna la lista de identificadores de proyectos de Jira asignados a un usuario."
)
async def get_user_projects(
    id_usuario: int,
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user, scopes=["jira:read"])
):
    _verify_admin(current_user)
    
    target_user = db.query(User).filter(User.id_usuario == id_usuario).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    proj_ids = [p.id_proyecto for p in target_user.proyectos_asignados]
    return {"id_usuario": id_usuario, "proyectos": proj_ids}

@router.post(
    "/{id_usuario}/projects",
    summary="Vincular proyectos a usuario (HU-005 CA-01, CA-03)",
    description="Reemplaza la lista de proyectos vinculados al usuario."
)
async def assign_user_projects(
    id_usuario: int,
    payload: UserProjectsPayload,
    db: Session = Depends(get_db),
    current_user: User = Security(get_current_user, scopes=["admin"])
):
    _verify_admin(current_user)

    target_user = db.query(User).filter(User.id_usuario == id_usuario).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Eliminar asignaciones previas
    db.query(UserProject).filter(UserProject.id_usuario == id_usuario).delete()

    # Insertar nuevas asignaciones sin duplicados (HU-005 CA-01)
    unique_proj_ids = set(payload.id_proyectos)
    for p_id in unique_proj_ids:
        # Verificar que el proyecto exista en BD
        proj_exists = db.query(Proyecto).filter(Proyecto.id_proyecto == p_id).first()
        if proj_exists:
            db.add(UserProject(id_usuario=id_usuario, id_proyecto=p_id))

    db.commit()
    db.refresh(target_user)

    updated_proj_ids = [p.id_proyecto for p in target_user.proyectos_asignados]
    return {
        "status": "success",
        "message": f"Proyectos vinculados correctamente al usuario {target_user.email}.",
        "id_usuario": id_usuario,
        "proyectos_asignados": updated_proj_ids
    }
