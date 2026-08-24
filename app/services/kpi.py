# app/services/kpi.py
# Servicio de cálculo de Indicadores Clave de Rendimiento (KPIs) del motor analítico de MCHAV Analytics
# Implementa la lógica de cálculo para Velocity, Throughput, Lead Time y Cycle Time (a nivel global y por Sprint)

from sqlalchemy.orm import Session
from sqlalchemy import select, func, case
from datetime import datetime, timezone
import app.models as models
from app.repositories import project_repo, mapping_repo, issue_repo, kpi_repo, sprint_repo

def get_issue_cycle_time_days(issue: models.Issue, in_progress_statuses: set[str] = None) -> float:
    """
    Calcula el tiempo de ciclo (Cycle Time) en días flotantes para un ticket individual resuelto.
    - Identifica la fecha exacta de la primera transición hacia un estado 'En Progreso' / 'In Progress'.
    - Resta dicha fecha de la estampa de tiempo de resolución (resolved_at).
    - Si no existen transiciones registradas a 'En Progreso', utiliza la fecha de creación (Lead Time Fallback).
    """
    if not issue.resolved_at:
        return 0.0
        
    # Nombres de estado por defecto si no se especifican mapeos personalizados
    if not in_progress_statuses:
        in_progress_statuses = {"in progress", "en progreso", "desarrollo", "in development", "doing", "active", "en desarrollo"}
        
    # Ordenar transiciones cronológicamente por fecha de cambio
    transitions = sorted(issue.transiciones, key=lambda t: t.fecha_cambio)
    
    first_progress_date = None
    for t in transitions:
        if t.estado_nuevo and t.estado_nuevo.lower() in in_progress_statuses:
            first_progress_date = t.fecha_cambio
            break
            
    if first_progress_date:
        delta = issue.resolved_at - first_progress_date
        return max(0.0, delta.total_seconds() / 86400.0) # Convertir segundos a días
    else:
        delta = issue.resolved_at - issue.created_at
        return max(0.0, delta.total_seconds() / 86400.0)

def calculate_and_save_kpis(db: Session, proyecto_id: str):
    """
    Calcula y persiste las agregaciones de KPIs para un proyecto completo y para cada uno de sus sprints.
    1. Consulta los mapeos de estado configurados ('IN_PROGRESS').
    2. Delega el cálculo matemático de Velocity, Throughput, Lead Time y Cycle Time al repositorio SQL.
    3. Almacena o actualiza la entrada global del proyecto en 'kpis_historicos' (donde id_sprint es None).
    4. Recorre cada sprint ordenado cronológicamente y calcula/actualiza sus KPIs individuales.
    """
    proyecto = project_repo.get(db, id=proyecto_id)
    if not proyecto:
        print(f"Error calculating KPIs: Project {proyecto_id} not found")
        return
        
    # Consultar mapeos personalizados para determinar qué estados significan 'En Progreso'
    mappings = mapping_repo.get_by_project_and_base(db, proyecto_id, "IN_PROGRESS")
    
    if mappings:
        in_progress_statuses = {m.estado_jira.lower() for m in mappings}
    else:
        in_progress_statuses = {"in progress", "en progreso", "desarrollo", "in development", "doing", "active", "en desarrollo"}
        
    # 1. Obtener métricas agregadas globales del proyecto vía SQL
    general_stats = issue_repo.get_resolved_stats_by_project(db, proyecto_id, in_progress_statuses)
    
    total_sp, throughput, avg_lead_time, avg_cycle_time = general_stats
    
    general_kpi = kpi_repo.get_general_kpi(db, proyecto_id)
    now_utc = datetime.now(timezone.utc)
    
    kpi_in = {
        "id_proyecto": proyecto_id,
        "id_sprint": None,
        "velocity_total_sp": float(total_sp),
        "velocity_promedio_historico": float(total_sp),
        "throughput_issues": int(throughput),
        "lead_time_promedio_dias": float(avg_lead_time),
        "cycle_time_promedio_dias": float(avg_cycle_time),
        "fecha_calculo": now_utc
    }
    
    if not general_kpi:
        kpi_repo.create(db, obj_in=kpi_in)
    else:
        kpi_repo.update(db, db_obj=general_kpi, obj_in=kpi_in)
        
    # 2. Obtener sprints del proyecto y ordenarlos por fecha de finalización o inicio
    sprints = sprint_repo.get_by_project(db, proyecto_id)
    sprint_velocities = []
    
    def get_sort_key(s):
        dt = s.fecha_finalizacion or s.fecha_fin or s.fecha_inicio
        if dt:
            return dt.timestamp()
        return float('inf')
        
    sorted_sprints = sorted(sprints, key=get_sort_key)
    
    # 3. Calcular métricas individuales por sprint
    for sprint in sorted_sprints:
        sprint_stats = issue_repo.get_resolved_stats_by_sprint(db, sprint.id_sprint, in_progress_statuses)
        
        s_total_sp, s_throughput, s_avg_lead_time, s_avg_cycle_time = sprint_stats
        
        if sprint.estado.lower() in ("closed", "completado", "terminado"):
            sprint_velocities.append(float(s_total_sp))
            
        # Calcular el promedio histórico móvil de velocidad de sprints cerrados previa o actualmente
        avg_historical_velocity = sum(sprint_velocities) / len(sprint_velocities) if sprint_velocities else 0.0
        
        sprint_kpi = kpi_repo.get_sprint_kpi(db, proyecto_id, sprint.id_sprint)
        
        s_kpi_in = {
            "id_proyecto": proyecto_id,
            "id_sprint": sprint.id_sprint,
            "velocity_total_sp": float(s_total_sp),
            "velocity_promedio_historico": float(avg_historical_velocity),
            "throughput_issues": int(s_throughput),
            "lead_time_promedio_dias": float(s_avg_lead_time),
            "cycle_time_promedio_dias": float(s_avg_cycle_time),
            "fecha_calculo": now_utc
        }

        if not sprint_kpi:
            kpi_repo.create(db, obj_in=s_kpi_in)
        else:
            kpi_repo.update(db, db_obj=sprint_kpi, obj_in=s_kpi_in)
            
    print(f"SUCCESS: KPIs calculados para el proyecto {proyecto_id}")
