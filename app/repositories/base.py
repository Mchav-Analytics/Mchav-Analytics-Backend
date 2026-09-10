# app/repositories/base.py
# Módulo con la clase base genérica del patrón Repository / DAO (Data Access Object)
# Abstrae y estandariza las operaciones comunes CRUD (Create, Read, Update, Delete) para cualquier modelo ORM

from typing import Any, Dict, Generic, List, Optional, Type, TypeVar, Union
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import Base

# Variable de tipo genérica restringida a subclases del modelo Base de SQLAlchemy
ModelType = TypeVar("ModelType", bound=Base)

class CRUDBase(Generic[ModelType]):
    """
    Clase genérica con implementaciones por defecto para Crear, Leer, Actualizar y Eliminar (CRUD).
    Evita la duplicación de código genérico de acceso a datos en repositorios específicos.
    """

    def __init__(self, model: Type[ModelType]):
        """
        Inicializa el objeto CRUD asignando la clase de modelo SQLAlchemy correspondiente.
        """
        self.model = model

    def get(self, db: Session, id: Any) -> Optional[ModelType]:
        """
        Busca y retorna una única entidad por su clave primaria (ID).
        Retorna None si el registro no existe en la base de datos.
        """
        return db.get(self.model, id)

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        sort: Optional[str] = None,
        order: str = "asc"
    ) -> List[ModelType]:
        """
        Obtiene una lista paginada de entidades con opciones de ordenamiento dinámico.
        - skip: número de registros a omitir (desplazamiento / offset)
        - limit: número máximo de registros a retornar
        - sort: nombre del atributo del modelo para ordenar
        - order: dirección del ordenamiento ('asc' o 'desc')
        """
        query = db.query(self.model)
        
        # Aplicar ordenamiento dinámico si el modelo posee el campo especificado
        if sort and hasattr(self.model, sort):
            field = getattr(self.model, sort)
            if order.lower() == "desc":
                query = query.order_by(field.desc())
            else:
                query = query.order_by(field.asc())
                
        # Aplicar desplazamiento y límite para paginación eficiente
        return query.offset(skip).limit(limit).all()

    def create(self, db: Session, *, obj_in: Dict[str, Any]) -> ModelType:
        """
        Instancia, persiste en BD y retorna un nuevo registro a partir de un diccionario de atributos.
        Realiza el commit y refresh automáticos para obtener los IDs autogenerados.
        """
        db_obj = self.model(**obj_in)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(self, db: Session, *, db_obj: ModelType, obj_in: Dict[str, Any]) -> ModelType:
        """
        Actualiza los campos de un objeto ORM existente usando los valores de un diccionario.
        Realiza el commit y refresh automáticos.
        """
        obj_data = obj_in
        for field in obj_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, obj_data[field])
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> ModelType:
        """
        Elimina un registro de la base de datos por su clave primaria (ID) y realiza el commit.
        """
        obj = db.get(self.model, id)
        if obj:
            db.delete(obj)
            db.commit()
        return obj
