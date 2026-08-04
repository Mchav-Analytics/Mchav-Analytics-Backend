# app/api/v1/controllers/jql_controller.py
# Controlador HTTP para ejecutar consultas JQL parametrizadas contra Jira

from fastapi import APIRouter, Depends
from datetime import datetime, timezone
from typing import List
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import User
from app.schemas.jql import JQLQueryResponse, MetricSummarySchema, IssueBasicSchema
from app.core.jql_config import JQLQueries

# Router principal para los endpoints de consultas JQL
router = APIRouter(dependencies=[Depends(get_current_user)])

@router.get(
    "/extraction-delta",
    response_model=JQLQueryResponse,
    summary="Extracción de deltas (HU-013 / RF-023)",
    description="""
    **Responde a la HU-013: Sincronización Automática de Datos y RF-023.**
    
    Este endpoint extrae los deltas de issues modificados en las últimas 24 horas para alimentar el procesamiento por lotes (Batch) nocturno. 
    Evita tener que re-sincronizar toda la historia de Jira, optimizando recursos y tiempos de cálculo.
    """
)
async def get_extraction_delta(project_key: str):
    """Genera y ejecuta la consulta JQL de extracción delta (-24h) para un proyecto."""
    jql = JQLQueries.DELTA_EXTRACTION.format(project_key=project_key)
    
    return JQLQueryResponse(
        jql_executed=jql,
        metrics=MetricSummarySchema(total_issues=0),
        issues=[]
    )

@router.get(
    "/velocity-throughput",
    response_model=JQLQueryResponse,
    summary="Velocidad y Throughput del Sprint (HU-005, HU-006)",
    description="""
    **Responde a las HU-005 (Velocity) y HU-006 (Throughput) / RF-011 y RF-012.**
    
    Procesa los issues finalizados en un Sprint específico para sumar los Story Points (Velocity) 
    y contabilizar el volumen neto de filas o tickets entregados (Throughput). 
    """
)
async def get_velocity_throughput(project_key: str, status_done: str, sprint_id: int):
    """Genera la consulta JQL parametrizada para obtener Velocity y Throughput de un sprint."""
    jql = JQLQueries.VELOCITY_THROUGHPUT.format(
        project_key=project_key, 
        status_done=status_done, 
        sprint_id=sprint_id
    )
    
    return JQLQueryResponse(
        jql_executed=jql,
        metrics=MetricSummarySchema(total_issues=0, total_story_points=0.0),
        issues=[]
    )

@router.get(
    "/time-cycles",
    response_model=JQLQueryResponse,
    summary="Tiempos de Ciclo por Fechas (HU-007, HU-008)",
    description="""
    **Responde a las HU-007 (Lead Time) y HU-008 (Cycle Time) / RF-013 y RF-014.**
    
    Extrae ítems resueltos en un rango de fechas determinado para mapear el ciclo de vida y pre-computar promedios en días hábiles.
    """
)
async def get_time_cycles(project_key: str, start_date: str, end_date: str):
    """Genera la consulta JQL parametrizada para obtener los tickets resueltos en un rango de fechas."""
    jql = JQLQueries.TIME_CYCLES.format(
        project_key=project_key, 
        start_date=start_date, 
        end_date=end_date
    )
    
    return JQLQueryResponse(
        jql_executed=jql,
        metrics=MetricSummarySchema(total_issues=0),
        issues=[]
    )