# app/schemas/project_schema.py
# Esquemas DTO de Pydantic para el dominio de Proyectos y Mapeos de Estado

from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ProjectMappingPayload(BaseModel):
    """Esquema para guardar la configuración de mapeo de estados personalizada de un proyecto."""
    mapping_estados: Optional[Dict[str, Any]] = None # Diccionario con las asignaciones de estados
    columnas: Optional[List[str]] = None             # Columnas visibles configuradas

class ProjectResponse(BaseModel):
    """Esquema de respuesta DTO para listas y detalles de proyectos."""
    id_proyecto: str
    key_proyecto: str
    nombre: str
    id_board: Optional[int] = None
    mapping_estados: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True # Permite instanciar desde modelos ORM de SQLAlchemy
