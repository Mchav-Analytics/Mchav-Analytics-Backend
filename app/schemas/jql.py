# app/schemas/jql.py
# Esquemas DTO de Pydantic para la representacion unificada de resultados de consultas JQL

from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class IssueBasicSchema(BaseModel):
    """Esquema seguro para representar un ticket devuelto por Jira."""
    issue_key: str = Field(..., description="Llave del ticket (Ej: MCHAV-123)")
    summary: str = Field(..., description="Título o resumen del ticket")
    status: str = Field(..., description="Estado actual del ticket")
    created_at: datetime = Field(..., description="Fecha de creación del ticket")
    resolved_at: Optional[datetime] = Field(None, description="Fecha de resolución, si aplica")
    story_points: float = Field(0.0, description="Puntos de historia asignados")

class MetricSummarySchema(BaseModel):
    """Esquema para representar la agregación o cálculo matemático de una consulta JQL."""
    total_issues: int = Field(0, description="Total de tickets devueltos por la consulta")
    total_story_points: float = Field(0.0, description="Suma neta de Story Points (útil para Velocity)")
    average_lead_time_days: Optional[float] = Field(None, description="Promedio de Lead Time en días hábiles (si aplica)")

class JQLQueryResponse(BaseModel):
    """Envoltura estandarizada para responder a las consultas JQL expuestas."""
    jql_executed: str = Field(..., description="La query exacta que se generó y ejecutó contra Jira")
    metrics: MetricSummarySchema = Field(..., description="Cálculos estadísticos resumidos de los tickets")
    issues: List[IssueBasicSchema] = Field(..., description="Lista de tickets en formato unificado")
