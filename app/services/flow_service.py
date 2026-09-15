# app/services/flow_service.py

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func
from datetime import datetime, timezone, timedelta
import statistics
import app.models as models
from typing import List, Dict, Any, Optional

class FlowStateCategorizer:
    """
    Categoriza estados de Jira en ACTIVE, WAITING, BLOCKED, DONE.
    Utiliza MapeoEstado si existe, de lo contrario infiere por nombre.
    """
    def __init__(self, db: Session, project_id: str):
        self.db = db
        self.project_id = project_id
        # Mapeos directos si existen en la BD (TODO, IN_PROGRESS, DONE)
        self.mappings = db.query(models.MapeoEstado).filter(models.MapeoEstado.id_proyecto == project_id).all()
        self.mapping_dict = {m.estado_jira.lower(): m.estado_base.lower() for m in self.mappings}

        # Palabras clave para inferir si no hay mapeo específico de flujo (ACTIVE/WAITING/BLOCKED)
        # Incluye términos en inglés y español (Jira Cloud en español)
        self.done_keywords = [
            "done", "finalizado", "cerrado", "resuelto", "completado", "resolved", "closed", "finished"
        ]
        self.blocked_keywords = [
            "block", "impediment", "bloqueado", "impedido", "detenido"
        ]
        self.waiting_keywords = [
            "wait", "review", "qa", "test", "ready", "espera", "revisión", "revision",
            "listo", "pendiente", "aprobación", "aprobacion"
        ]
        self.active_keywords = [
            "progress", "doing", "develop", "progreso", "desarrollo", "active",
            "en curso", "en progreso", "in progress", "working", "trabajando"
        ]

    def categorize_state(self, state_name: str) -> str:
        if not state_name:
            return "WAITING"

        lower_state = state_name.lower()

        # 1. Done primero para no confundir con otras categorías
        if any(k in lower_state for k in self.done_keywords):
            return "DONE"

        # 2. Inferir por palabras clave específicas de flujo
        if any(k in lower_state for k in self.blocked_keywords):
            return "BLOCKED"
        if any(k in lower_state for k in self.active_keywords):
            return "ACTIVE"
        if any(k in lower_state for k in self.waiting_keywords):
            return "WAITING"

        # 3. Fallback a MapeoEstado base
        base_state = self.mapping_dict.get(lower_state, "todo")
        if base_state == "in_progress":
            return "ACTIVE"
        if base_state == "done":
            return "DONE"

        return "WAITING"  # Por defecto todo lo que no se reconoce

def get_issue_flow_timeline(issue: models.Issue) -> List[Dict[str, Any]]:
    """
    Calcula el tiempo que pasó la issue en cada estado usando sus transiciones.
    Retorna una lista de intervalos.
    """
    transitions = sorted(issue.transiciones, key=lambda t: t.fecha_cambio)
    if not transitions:
        # Si no hay transiciones, asumimos que estuvo en su estado actual desde la creación
        now = issue.resolved_at or datetime.now()
        if now.tzinfo:
            now = now.replace(tzinfo=None)
        
        created = issue.created_at
        if created and created.tzinfo:
            created = created.replace(tzinfo=None)
            
        duration = max(0.0, (now - created).total_seconds())
        return [{
            "state": issue.status_actual,
            "start": issue.created_at,
            "end": now,
            "duration_seconds": duration
        }]

    timeline = []
    # El primer estado comienza en created_at y termina en la primera transición
    current_state = transitions[0].estado_anterior or "To Do"
    last_time = issue.created_at
    
    for t in transitions:
        end_time = t.fecha_cambio
        duration = max(0.0, (end_time - last_time).total_seconds())
        timeline.append({
            "state": current_state,
            "start": last_time,
            "end": end_time,
            "duration_seconds": duration
        })
        current_state = t.estado_nuevo
        last_time = end_time
        
    # El último estado va desde la última transición hasta resolved_at o ahora
    now = issue.resolved_at or datetime.now()
    if now.tzinfo:
        now = now.replace(tzinfo=None)
    if last_time and last_time.tzinfo:
        last_time = last_time.replace(tzinfo=None)
    duration = max(0.0, (now - last_time).total_seconds())
    timeline.append({
        "state": current_state,
        "start": last_time,
        "end": now,
        "duration_seconds": duration
    })
    
    return timeline

def calculate_cycle_time_percentiles(db: Session, project_id: str, sprint_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Calcula percentiles de Cycle Time (P50, P75, P85, P95) usando solo tickets resueltos.
    """
    query = db.query(models.Issue).filter(
        models.Issue.id_proyecto == project_id,
        models.Issue.resolved_at.isnot(None)
    )
    if sprint_id:
        query = query.filter(models.Issue.id_sprint == sprint_id)
        
    issues = query.all()
    if not issues:
        return {"avg": 0, "p50": 0, "p75": 0, "p85": 0, "p95": 0, "count": 0}
        
    categorizer = FlowStateCategorizer(db, project_id)
    cycle_times = []
    
    for issue in issues:
        timeline = get_issue_flow_timeline(issue)
        started_processing = False
        total_seconds = 0
        
        for t in timeline:
            cat = categorizer.categorize_state(t["state"])
            if cat in ["ACTIVE", "WAITING", "BLOCKED"] and not started_processing:
                started_processing = True
                
            if started_processing:
                if cat == "DONE":
                    break
                total_seconds += t["duration_seconds"]
                
        if total_seconds > 0:
            cycle_times.append(total_seconds / 86400.0) # a días
            
    if not cycle_times:
         return {"avg": 0, "p50": 0, "p75": 0, "p85": 0, "p95": 0, "count": 0}

    cycle_times.sort()
    
    if len(cycle_times) >= 2:
        quantiles = statistics.quantiles(cycle_times, n=100, method='inclusive')
        p50 = quantiles[49]
        p75 = quantiles[74]
        p85 = quantiles[84]
        p95 = quantiles[94]
    else:
        p50 = p75 = p85 = p95 = cycle_times[0]
        
    return {
        "avg": round(sum(cycle_times) / len(cycle_times), 1),
        "p50": round(p50, 1),
        "p75": round(p75, 1),
        "p85": round(p85, 1),
        "p95": round(p95, 1),
        "count": len(cycle_times)
    }

def calculate_flow_efficiency(db: Session, project_id: str, sprint_id: Optional[str] = None) -> Dict[str, Any]:
    """
    Calcula Flow Efficiency: Active Time / (Active + Waiting + Blocked) * 100
    """
    query = db.query(models.Issue).filter(models.Issue.id_proyecto == project_id)
    if sprint_id:
        query = query.filter(models.Issue.id_sprint == sprint_id)
        
    issues = query.all()
    categorizer = FlowStateCategorizer(db, project_id)
    
    total_active = 0.0
    total_waiting = 0.0
    total_blocked = 0.0
    
    for issue in issues:
        timeline = get_issue_flow_timeline(issue)
        started_processing = False
        
        for t in timeline:
            cat = categorizer.categorize_state(t["state"])
            
            if cat in ["ACTIVE", "WAITING", "BLOCKED"] and not started_processing:
                started_processing = True
                
            if started_processing and cat != "DONE":
                if cat == "ACTIVE":
                    total_active += t["duration_seconds"]
                elif cat == "WAITING":
                    total_waiting += t["duration_seconds"]
                elif cat == "BLOCKED":
                    total_blocked += t["duration_seconds"]

    total = total_active + total_waiting + total_blocked
    if total == 0:
        return {"active_pct": 0, "waiting_pct": 0, "blocked_pct": 0, "total_days": 0, "active_days": 0, "waiting_days": 0, "blocked_days": 0}
        
    return {
        "active_pct": round((total_active / total) * 100, 1),
        "waiting_pct": round((total_waiting / total) * 100, 1),
        "blocked_pct": round((total_blocked / total) * 100, 1),
        "total_days": round(total / 86400.0, 1),
        "active_days": round(total_active / 86400.0, 1),
        "waiting_days": round(total_waiting / 86400.0, 1),
        "blocked_days": round(total_blocked / 86400.0, 1)
    }

def detect_bottlenecks(db: Session, project_id: str, sprint_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query = db.query(models.Issue).filter(models.Issue.id_proyecto == project_id)
    if sprint_id:
        query = query.filter(models.Issue.id_sprint == sprint_id)
        
    issues = query.all()
    categorizer = FlowStateCategorizer(db, project_id)
    
    state_durations = {}
    state_active_issues = {}
    
    for issue in issues:
        timeline = get_issue_flow_timeline(issue)
        
        for t in timeline:
            state = t["state"]
            cat = categorizer.categorize_state(state)
            if cat in ["DONE", "To Do"]: continue
            
            duration = t["duration_seconds"] / 86400.0
            
            if state not in state_durations:
                state_durations[state] = []
                state_active_issues[state] = 0
                
            state_durations[state].append(duration)
            
        if not issue.resolved_at:
            curr_state = issue.status_actual
            if curr_state in state_active_issues:
                state_active_issues[curr_state] += 1
            else:
                state_active_issues[curr_state] = 1

    results = []
    total_all_durations = sum(sum(durs) for durs in state_durations.values())
    
    for state, durations in state_durations.items():
        if not durations:
            continue
            
        durations.sort()
        count = len(durations)
        avg = sum(durations) / count
        
        if count >= 2:
            quantiles = statistics.quantiles(durations, n=100, method='inclusive')
            p50 = quantiles[49]
            p75 = quantiles[74]
            p95 = quantiles[94]
        else:
            p50 = p75 = p95 = durations[0]
            
        pct_of_total = (sum(durations) / total_all_durations * 100) if total_all_durations > 0 else 0
            
        results.append({
            "state": state,
            "avg": round(avg, 1),
            "p50": round(p50, 1),
            "p75": round(p75, 1),
            "p95": round(p95, 1),
            "current_issues": state_active_issues.get(state, 0),
            "pct_of_total": round(pct_of_total, 1)
        })
        
    results.sort(key=lambda x: x["p75"], reverse=True)
    return results

def get_blockers(db: Session, project_id: str) -> List[Dict[str, Any]]:
    issues = db.query(models.Issue).filter(
        models.Issue.id_proyecto == project_id,
        models.Issue.resolved_at.isnot(None) == False
    ).all()
    
    categorizer = FlowStateCategorizer(db, project_id)
    blockers = []
    
    for issue in issues:
        cat = categorizer.categorize_state(issue.status_actual)
        if cat == "BLOCKED":
            timeline = get_issue_flow_timeline(issue)
            current = timeline[-1]
            duration_days = current["duration_seconds"] / 86400.0
            
            blockers.append({
                "issue_key": issue.key_issue,
                "title": issue.summary,
                "state": issue.status_actual,
                "duration_days": round(duration_days, 1),
                "assignee": issue.assignee_name or "Unassigned",
                "blocked_since": current["start"].isoformat()
            })
            
    blockers.sort(key=lambda x: x["duration_days"], reverse=True)
    return blockers

def get_aging_work(db: Session, project_id: str) -> List[Dict[str, Any]]:
    issues = db.query(models.Issue).filter(
        models.Issue.id_proyecto == project_id,
        models.Issue.resolved_at.isnot(None) == False
    ).all()
    
    categorizer = FlowStateCategorizer(db, project_id)
    aging_list = []
    
    for issue in issues:
        timeline = get_issue_flow_timeline(issue)
        started_processing = False
        total_seconds = 0
        
        for t in timeline:
            cat = categorizer.categorize_state(t["state"])
            if cat in ["ACTIVE", "WAITING", "BLOCKED"] and not started_processing:
                started_processing = True
                
            if started_processing:
                total_seconds += t["duration_seconds"]
                
        if started_processing and total_seconds > 0:
            aging_list.append({
                "issue_key": issue.key_issue,
                "title": issue.summary,
                "state": issue.status_actual,
                "aging_days": round(total_seconds / 86400.0, 1),
                "assignee": issue.assignee_name or "Unassigned",
                "sprint": issue.sprint_activo.nombre if issue.sprint_activo else "Backlog"
            })
            
    aging_list.sort(key=lambda x: x["aging_days"], reverse=True)
    return aging_list

def calculate_cfd_and_wip(db: Session, project_id: str, sprint_id: Optional[str] = None) -> Dict[str, Any]:
    query = db.query(models.Issue).filter(models.Issue.id_proyecto == project_id)
    if sprint_id:
        query = query.filter(models.Issue.id_sprint == sprint_id)
        
    issues = query.all()
    categorizer = FlowStateCategorizer(db, project_id)
    
    wip_summary = {}
    total_wip = 0
    
    for issue in issues:
        if not issue.resolved_at:
            cat = categorizer.categorize_state(issue.status_actual)
            if cat in ["ACTIVE", "WAITING", "BLOCKED"]:
                state = issue.status_actual
                wip_summary[state] = wip_summary.get(state, 0) + 1
                total_wip += 1
                
    cfd_data = []
    now = datetime.now(timezone.utc).replace(tzinfo=None)  # naive UTC para comparar con timeline
    start_date = now - timedelta(days=30)

    def to_naive_utc(dt):
        """Convierte cualquier datetime a naive UTC para comparaciones consistentes."""
        if dt is None:
            return now
        if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
            return dt.astimezone(timezone.utc).replace(tzinfo=None)
        return dt

    for i in range(31):
        day = start_date + timedelta(days=i)
        day_end = day.replace(hour=23, minute=59, second=59)

        day_counts = {"To Do": 0, "Active": 0, "Waiting": 0, "Blocked": 0, "Done": 0}

        for issue in issues:
            issue_created = to_naive_utc(issue.created_at)
            if issue_created > day_end:
                continue

            timeline = get_issue_flow_timeline(issue)
            state_at_day = None
            for t in timeline:
                start = to_naive_utc(t["start"])
                end = to_naive_utc(t["end"])

                if start <= day_end and end >= day_end:
                    state_at_day = t["state"]
                    break
                elif end <= day_end:
                    state_at_day = t["state"]

            if state_at_day:
                cat = categorizer.categorize_state(state_at_day)
                if cat == "ACTIVE": day_counts["Active"] += 1
                elif cat == "WAITING": day_counts["Waiting"] += 1
                elif cat == "BLOCKED": day_counts["Blocked"] += 1
                elif cat == "DONE": day_counts["Done"] += 1
                else: day_counts["To Do"] += 1

        cfd_data.append({
            "date": day.strftime("%Y-%m-%d"),
            **day_counts
        })

    return {
        "wip": {
            "total": total_wip,
            "distribution": [{"state": k, "count": v} for k, v in wip_summary.items()]
        },
        "cfd": cfd_data
    }
