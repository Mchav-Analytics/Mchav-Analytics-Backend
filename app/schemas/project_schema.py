from typing import Optional, List, Dict, Any
from pydantic import BaseModel

class ProjectMappingPayload(BaseModel):
    mapping_estados: Optional[Dict[str, Any]] = None
    columnas: Optional[List[str]] = None

class ProjectResponse(BaseModel):
    id_proyecto: int
    key_proyecto: str
    nombre: str
    id_board: Optional[int] = None
    mapping_estados: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
