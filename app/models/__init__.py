# app/models/__init__.py
# Módulo de inicialización de modelos ORM
# Utiliza el Patrón Fachada (Facade Pattern) para re-exportar todos los modelos de dominio.
# Esto permite realizar importaciones centralizadas con 'import app.models as models' o 'from app.models import ...'

# Base declarativa común de SQLAlchemy
from app.core.database import Base

# Modelos del dominio de autenticación y usuarios
from .auth import Role, User

# Modelos del dominio de Jira (Proyectos, Sprints, Issues, Transiciones, Mapeos de Estado)
from .jira import issues_sprints, Proyecto, Sprint, Issue, TransicionEstadoIssue, MapeoEstado

# Modelos del dominio de métricas y auditoría (KPIs Históricos, Logs de Sincronización)
from .metrics import KpisHistoricos, LogsSincronizacion

# Lista explícita de símbolos exportados para la importación estilo wildcard ('from app.models import *')
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
