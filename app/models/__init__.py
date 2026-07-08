# Patrón Fachada (Facade Pattern)
# Importamos todos los modelos de sus respectivos dominios y los exportamos 
# para que el resto del sistema pueda hacer 'import app.models as models' sin romperse.

from app.core.database import Base

from .auth import Role, User
from .jira import issues_sprints, Proyecto, Sprint, Issue, TransicionEstadoIssue, MapeoEstado
from .metrics import KpisHistoricos, LogsSincronizacion

# Opcional: Definimos __all__ para explicitar qué clases se exportan cuando alguien hace 'from app.models import *'
__all__ = [
    "Base",
    "Role",
    "User",
    "issues_sprints",
    "Proyecto",
    "Sprint",
    "Issue",
    "TransicionEstadoIssue",
    "MapeoEstado",
    "KpisHistoricos",
    "LogsSincronizacion"
]
