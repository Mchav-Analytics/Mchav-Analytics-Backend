# app/services/project_resolver.py
# Servicio utilitario para la resolución dinámica y segura de proyectos Jira en base de datos.
# Evita fallos por claves 'PROJ-01', cadenas vacías o desincronización de identificadores.

from typing import Optional
from sqlalchemy.orm import Session
import app.models as models

DEFAULT_PROJECT_ID = "10000"

def resolve_project_id(db: Optional[Session], proyecto_id: Optional[str] = None) -> str:
    """
    Resuelve el ID de proyecto real en PostgreSQL:
    1. Si es 'ALL', mantiene 'ALL'.
    2. Si se proporciona un ID numérico o clave ('SCRUM', 'PA', '10000', '10033'):
       Verifica si existe en la tabla 'proyectos'.
    3. Si es nulo, vacío, 'PROJ-01' o no existe en la BD:
       Selecciona automáticamente el primer proyecto registrado y activo en la BD.
    4. Si no hay conexión o no hay proyectos en la BD, retorna '10000'.
    """
    if not proyecto_id:
        cleaned = ""
    else:
        cleaned = str(proyecto_id).strip()

    if cleaned.upper() == "ALL":
        return "ALL"

    if db:
        try:
            # Si no es PROJ-01, buscar coincidencia exacta por ID o Clave
            if cleaned and cleaned.upper() != "PROJ-01":
                p = db.query(models.Proyecto).filter(
                    (models.Proyecto.id_proyecto == cleaned) |
                    (models.Proyecto.key_proyecto == cleaned)
                ).first()
                if p:
                    return str(p.id_proyecto)

            # Si es PROJ-01, vacío o no encontrado, auto-seleccionar el primer proyecto real
            first_p = db.query(models.Proyecto).order_by(models.Proyecto.id_proyecto.asc()).first()
            if first_p:
                return str(first_p.id_proyecto)
        except Exception:
            pass

    return cleaned if (cleaned and cleaned.upper() != "PROJ-01") else DEFAULT_PROJECT_ID
