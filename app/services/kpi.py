from sqlalchemy.orm import Session
from datetime import datetime, timezone
import app.models as models

def get_issue_cycle_time_days(issue: models.Issue, in_progress_statuses: set[str] = None) -> float:
    if not issue.resolved_at:
        return 0.0
        
    if not in_progress_statuses:
        in_progress_statuses = {"in progress", "en progreso", "desarrollo", "in development", "doing", "active", "en desarrollo"}
        
    transitions = sorted(issue.transiciones, key=lambda t: t.fecha_cambio)
    
    first_progress_date = None
    for t in transitions:
        if t.estado_nuevo and t.estado_nuevo.lower() in in_progress_statuses:
            first_progress_date = t.fecha_cambio
            break
            
    if first_progress_date:
        delta = issue.resolved_at - first_progress_date
        return max(0.0, delta.total_seconds() / 86400.0)
    else:
        delta = issue.resolved_at - issue.created_at
        return max(0.0, delta.total_seconds() / 86400.0)

def calculate_and_save_kpis(db: Session, proyecto_id: str):
    proyecto = db.query(models.Proyecto).filter(models.Proyecto.id_proyecto == proyecto_id).first()
    if not proyecto:
        print(f"Error calculating KPIs: Project {proyecto_id} not found")
        return
        
    # Obtener mapeo de estados personalizados desde la base de datos
    mappings = db.query(models.MapeoEstado).filter(
        models.MapeoEstado.id_proyecto == proyecto_id,
        models.MapeoEstado.estado_base == "IN_PROGRESS"
    ).all()
    
    if mappings:
        in_progress_statuses = {m.estado_jira.lower() for m in mappings}
    else:
        in_progress_statuses = None
        
    # --- CÁLCULO DE KPIS GENERALES DEL PROYECTO (id_sprint IS NULL) ---
    all_project_issues = db.query(models.Issue).filter(models.Issue.id_proyecto == proyecto_id).all()
    resolved_issues = [i for i in all_project_issues if i.resolved_at is not None]
    
    total_sp = sum(float(i.story_points or 0.0) for i in resolved_issues)
    throughput = len(resolved_issues)
    
    lead_times = []
    cycle_times = []
    
    for issue in resolved_issues:
        lt = (issue.resolved_at - issue.created_at).total_seconds() / 86400.0
        lead_times.append(max(0.0, lt))
        
        ct = get_issue_cycle_time_days(issue, in_progress_statuses)
        cycle_times.append(ct)
        
    avg_lead_time = sum(lead_times) / len(lead_times) if lead_times else 0.0
    avg_cycle_time = sum(cycle_times) / len(cycle_times) if cycle_times else 0.0
    
    general_kpi = db.query(models.KpisHistoricos).filter(
        models.KpisHistoricos.id_proyecto == proyecto_id,
        models.KpisHistoricos.id_sprint == None
    ).first()
    
    now_utc = datetime.now(timezone.utc)
    
    if not general_kpi:
        general_kpi = models.KpisHistoricos(
            id_proyecto=proyecto_id,
            id_sprint=None,
            velocity_total_sp=total_sp,
            velocity_promedio_historico=total_sp,
            throughput_issues=throughput,
            lead_time_promedio_dias=avg_lead_time,
            cycle_time_promedio_dias=avg_cycle_time,
            fecha_calculo=now_utc
        )
        db.add(general_kpi)
    else:
        general_kpi.velocity_total_sp = total_sp
        general_kpi.velocity_promedio_historico = total_sp
        general_kpi.throughput_issues = throughput
        general_kpi.lead_time_promedio_dias = avg_lead_time
        general_kpi.cycle_time_promedio_dias = avg_cycle_time
        general_kpi.fecha_calculo = now_utc
        
    # --- CÁLCULO DE KPIS POR SPRINT ---
    sprints = db.query(models.Sprint).filter(models.Sprint.id_proyecto == proyecto_id).all()
    sprint_velocities = []
    
    def get_sort_key(s):
        dt = s.fecha_finalizacion or s.fecha_fin or s.fecha_inicio
        if dt:
            return dt.timestamp()
        return float('inf')
        
    sorted_sprints = sorted(sprints, key=get_sort_key)
    
    for sprint in sorted_sprints:
        sprint_issues = db.query(models.Issue).filter(models.Issue.id_sprint == sprint.id_sprint).all()
        sprint_resolved = [i for i in sprint_issues if i.resolved_at is not None]
        
        s_total_sp = sum(float(i.story_points or 0.0) for i in sprint_resolved)
        s_throughput = len(sprint_resolved)
        
        s_lead_times = []
        s_cycle_times = []
        
        for issue in sprint_resolved:
            lt = (issue.resolved_at - issue.created_at).total_seconds() / 86400.0
            s_lead_times.append(max(0.0, lt))
            
            ct = get_issue_cycle_time_days(issue, in_progress_statuses)
            s_cycle_times.append(ct)
            
        s_avg_lead_time = sum(s_lead_times) / len(s_lead_times) if s_lead_times else 0.0
        s_avg_cycle_time = sum(s_cycle_times) / len(s_cycle_times) if s_cycle_times else 0.0
        
        if sprint.estado.lower() in ("closed", "completado", "terminado"):
            sprint_velocities.append(s_total_sp)
            
        avg_historical_velocity = sum(sprint_velocities) / len(sprint_velocities) if sprint_velocities else 0.0
        
        sprint_kpi = db.query(models.KpisHistoricos).filter(
            models.KpisHistoricos.id_proyecto == proyecto_id,
            models.KpisHistoricos.id_sprint == sprint.id_sprint
        ).first()
        
        if not sprint_kpi:
            sprint_kpi = models.KpisHistoricos(
                id_proyecto=proyecto_id,
                id_sprint=sprint.id_sprint,
                velocity_total_sp=s_total_sp,
                velocity_promedio_historico=avg_historical_velocity,
                throughput_issues=s_throughput,
                lead_time_promedio_dias=s_avg_lead_time,
                cycle_time_promedio_dias=s_avg_cycle_time,
                fecha_calculo=now_utc
            )
            db.add(sprint_kpi)
        else:
            sprint_kpi.velocity_total_sp = s_total_sp
            sprint_kpi.velocity_promedio_historico = avg_historical_velocity
            sprint_kpi.throughput_issues = s_throughput
            sprint_kpi.lead_time_promedio_dias = s_avg_lead_time
            sprint_kpi.cycle_time_promedio_dias = s_avg_cycle_time
            sprint_kpi.fecha_calculo = now_utc
            
    db.commit()
    print(f"SUCCESS: KPIs calculated for project {proyecto_id}")
