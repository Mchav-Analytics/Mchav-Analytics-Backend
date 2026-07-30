"""Puertos (interfaces) de la arquitectura limpia.

Los casos de uso dependen de estos contratos, no de HTTP/SQLAlchemy concretos.
Las implementaciones viven en datasources/ y repositories/.
"""

from app.ports.jira_gateway import JiraGateway
from app.ports.oauth_gateway import AtlassianOAuthGateway

__all__ = ["JiraGateway", "AtlassianOAuthGateway"]
