# app/api/v1/controllers/jql_controller.py
# Controlador HTTP para ejecutar consultas JQL parametrizadas contra Jira

from fastapi import APIRouter, Depends, HTTPException, Request, status
from datetime import datetime, timezone
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.orm import Session
import httpx

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import User
from app.schemas.jql import JQLQueryResponse, MetricSummarySchema, IssueBasicSchema
from app.core.jql_config import JQLQueries
from app.datasources.jira_datasource import JiraDatasource
from app.services.jira_sync import get_jira_auth_credentials
from app.api.v1 import deps

# Router principal para los endpoints de consultas JQL
router = APIRouter(dependencies=[Depends(get_current_user)])

class JQLExecutionPayload(BaseModel):
    jql: str
    max_results: Optional[int] = 50

def validate_jql_syntax(jql: str) -> bool:
    """
    HU-009 CA-02: Valida sintácticamente una consulta JQL previa a su ejecución.
    Verifica paréntesis balanceados, comillas abiertas/cerradas y palabras clave válidas.
    """
    if not jql or not jql.strip():
        raise HTTPException(
            status_code=400,
            detail="Sintaxis JQL inválida: La consulta no puede estar vacía."
        )

    stack = []
    in_quotes = False
    quote_char = None
    for char in jql:
        if char in ('"', "'"):
            if not in_quotes:
                in_quotes = True
                quote_char = char
            elif char == quote_char:
                in_quotes = False
                quote_char = None
        elif not in_quotes:
            if char == '(':
                stack.append('(')
            elif char == ')':
                if not stack:
                    raise HTTPException(
                        status_code=400,
                        detail="Sintaxis JQL inválida: Se encontró un paréntesis de cierre ')' sin su correspondiente apertura '('."
                    )
                stack.pop()

    if in_quotes:
        raise HTTPException(
            status_code=400,
            detail="Sintaxis JQL inválida: Comilla sin cerrar en la consulta."
        )

    if stack:
        raise HTTPException(
            status_code=400,
            detail="Sintaxis JQL inválida: Paréntesis de apertura '(' sin cerrar."
        )

    import re
    jql_upper = jql.upper()
    pattern = r'(\b(PROJECT|STATUS|CREATED|UPDATED|ISSUETYPE|ASSIGNEE|PRIORITY|SPRINT|STATUSCATEGORY|ORDER|AND|OR|IN|IS|WAS)\b|=|\!=|~)'
    
    if not re.search(pattern, jql_upper):
        raise HTTPException(
            status_code=400,
            detail="Sintaxis JQL inválida: La consulta no contiene un campo o filtro JQL reconocido (ejemplo: project = 'MCHAV')."
        )
    return True

@router.post(
    "/execute",
    summary="Ejecutar consulta JQL personalizada (HU-009)",
    description="Valida la sintaxis JQL e invoca la API REST de Jira retornando los resultados paginados."
)
async def execute_custom_jql(
    payload: JQLExecutionPayload,
    request: Request,
    db: Session = Depends(get_db)
):
    user_id = deps.get_current_user_id(request)
    user = deps.check_user_exists(db, user_id)

    # HU-009 CA-02: Validar sintaxis JQL antes de ejecutar
    validate_jql_syntax(payload.jql)

    try:
        base_jira_url, headers = get_jira_auth_credentials(db, user)
        async with httpx.AsyncClient(timeout=30.0) as client:
            res_data = await JiraDatasource.fetch_issues_jql(
                client,
                base_jira_url,
                headers,
                jql=payload.jql,
                max_results=payload.max_results or 50
            )
            issues_list = res_data.get("issues", [])
            return {
                "status": "success",
                "jql_executed": payload.jql,
                "total": res_data.get("total", len(issues_list)),
                "issues": issues_list
            }
    except Exception as e:
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(
            status_code=400,
            detail=f"Error al ejecutar la consulta JQL en Jira: {str(e)}"
        )

@router.get(
    "/presets",
    summary="Obtener Diccionario de Consultas JQL Recomendadas",
    description="Retorna el catálogo predefinido de consultas JQL estructuradas por categorías para proyectos."
)
def get_jql_presets(project_key: str = "SCRUM"):
    key = project_key.strip().upper() if project_key else "SCRUM"
    return {
        "status": "success",
        "project_key": key,
        "categories": [
            {
                "category": "Consultas Básicas del Proyecto",
                "queries": [
                    { "id": "all", "nombre": "Todas las Incidencias del Proyecto", "jql": f'project = "{key}"', "description": "Obtiene la totalidad de incidencias del proyecto." },
                    { "id": "todo", "nombre": "Pendientes por Iniciar (To Do)", "jql": f'project = "{key}" AND status in ("To Do", "Por hacer", "Pendiente")', "description": "Incidencias registradas aún no iniciadas." },
                    { "id": "in_progress", "nombre": "En Progreso (Trabajo Activo)", "jql": f'project = "{key}" AND status in ("In Progress", "En curso")', "description": "Incidencias en desarrollo actualmente." },
                    { "id": "done", "nombre": "Completadas (Done)", "jql": f'project = "{key}" AND status in ("Done", "Finalizado", "Completado")', "description": "Incidencias finalizadas con éxito." }
                ]
            },
            {
                "category": "Filtros de Control Operativo y Calidad",
                "queries": [
                    { "id": "high_priority", "nombre": "Alta Prioridad / Críticos Pendientes", "jql": f'project = "{key}" AND priority in (High, Highest, Alta) AND status not in ("Done", "Finalizado", "Completado")', "description": "Incidencias críticas pendientes de solución." },
                    { "id": "unassigned", "nombre": "Incidencias Sin Asignar", "jql": f'project = "{key}" AND assignee is EMPTY AND status not in ("Done", "Finalizado", "Completado")', "description": "Tareas pendientes sin responsable asignado." },
                    { "id": "bugs", "nombre": "Bugs y Errores Activos", "jql": f'project = "{key}" AND issuetype in (Bug, Error) AND status not in ("Done", "Finalizado", "Completado")', "description": "Fallas o bugs en estado activo." },
                    { "id": "recent_7d", "nombre": "Actualizadas en los últimos 7 días", "jql": f'project = "{key}" AND updated >= -7d ORDER BY updated DESC', "description": "Histórico reciente de cambios." }
                ]
            }
        ]
    }

@router.get(
    "/extraction-delta",
    response_model=JQLQueryResponse,
    summary="Extracción de deltas (HU-013 / RF-023)",
    description="Extracción delta (-24h) para sincronización."
)
async def get_extraction_delta(project_key: str):
    jql = JQLQueries.DELTA_EXTRACTION.format(project_key=project_key)
    return JQLQueryResponse(
        jql_executed=jql,
        metrics=MetricSummarySchema(total_issues=0),
        issues=[]
    )

@router.get(
    "/velocity-throughput",
    response_model=JQLQueryResponse,
    summary="Velocidad y Throughput del Sprint"
)
async def get_velocity_throughput(project_key: str, status_done: str, sprint_id: int):
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
    summary="Tiempos de Ciclo por Fechas"
)
async def get_time_cycles(project_key: str, start_date: str, end_date: str):
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