# app/services/flow_service.py

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, func
from datetime import datetime, timezone, timedelta
import statistics
import app.models as models
from typing import List, Dict, Any, Optional

from app.services.jira_normalizer import categorize_flow_state, DONE_STATUSES, IN_PROGRESS_STATUSES

DEFAULT_INITIAL_STATE = "To Do"

class FlowStateCategorizer:
    """
    Categoriza estados de Jira en ACTIVE, WAITING, BLOCKED, DONE.
    Utiliza MapeoEstado si existe, de lo contrario infiere por nombre
    usando el normalizador centralizado y bilingüe.
    """
    def __init__(self, db: Session, project_id: str):
        self.db = db
        self.project_id = project_id
        # Mapeos directos si existen en la BD (TODO, IN_PROGRESS, DONE)
        self.mappings = db.query(models.MapeoEstado).filter(models.MapeoEstado.id_proyecto == project_id).all()
        self.mapping_dict = {m.estado_jira.lower().strip(): m.estado_base.lower().strip() for m in self.mappings}

        # Palabras clave canónicas bilingües
        self.done_keywords = [
            "done", "finalizado", "listo", "cerrado", "resuelto", "completado",
            "resolved", "closed", "finished", "terminado"
        ]
        self.blocked_keywords = [
            "block", "impediment", "bloqueado", "impedido", "detenido", "impedimento"
        ]
        self.waiting_keywords = [
            "wait", "waiting", "review", "qa", "test", "ready", "espera",
            "revisión", "revision", "pendiente", "aprobación", "aprobacion"
        ]
        self.active_keywords = [
            "progress", "doing", "develop", "progreso", "desarrollo", "active",
            "en curso", "en progreso", "in progress", "working", "trabajando"
        ]

    def categorize_state(self, state_name: str) -> str:
        if not state_name:
            return "WAITING"

        lower_state = state_name.lower().strip()

        # 1. Verificar MapeoEstado explícito de la BD si existe
        base_state = self.mapping_dict.get(lower_state)
        if base_state == "done":
            return "DONE"
        if base_state == "in_progress":
            if any(k in lower_state for k in self.waiting_keywords):
                return "WAITING"
            return "ACTIVE"

        # 2. Delegar a la función unificada de categorización
        return categorize_flow_state(state_name, self.db, self.project_id)

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
    current_state = transitions[0].estado_anterior or DEFAULT_INITIAL_STATE
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

def _compute_issue_cycle_time(timeline: List[Dict[str, Any]], categorizer: FlowStateCategorizer) -> float:
    started_processing = False
    total_seconds = 0.0
    for t in timeline:
        cat = categorizer.categorize_state(t["state"])
        if cat in ["ACTIVE", "WAITING", "BLOCKED"] and not started_processing:
            started_processing = True
        if started_processing:
            if cat == "DONE":
                break
            total_seconds += t["duration_seconds"]
    return (total_seconds / 86400.0) if total_seconds > 0 else 0.0


def _compute_percentiles_summary(cycle_times: List[float]) -> Dict[str, Any]:
    if not cycle_times:
        return {"avg": 0, "p50": 0, "p75": 0, "p85": 0, "p95": 0, "count": 0}
    cycle_times.sort()
    if len(cycle_times) >= 2:
        quantiles = statistics.quantiles(cycle_times, n=100, method='inclusive')
        p50, p75, p85, p95 = quantiles[49], quantiles[74], quantiles[84], quantiles[94]
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
    cycle_times = [
        ct for issue in issues
        if (ct := _compute_issue_cycle_time(get_issue_flow_timeline(issue), categorizer)) > 0
    ]
    return _compute_percentiles_summary(cycle_times)


def _accumulate_flow_durations(timeline: List[Dict[str, Any]], categorizer: FlowStateCategorizer) -> tuple[float, float, float]:
    started_processing = False
    active = waiting = blocked = 0.0
    for t in timeline:
        cat = categorizer.categorize_state(t["state"])
        if cat in ["ACTIVE", "WAITING", "BLOCKED"] and not started_processing:
            started_processing = True
        if started_processing and cat != "DONE":
            if cat == "ACTIVE":
                active += t["duration_seconds"]
            elif cat == "WAITING":
                waiting += t["duration_seconds"]
            elif cat == "BLOCKED":
                blocked += t["duration_seconds"]
    return active, waiting, blocked


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
        act, wt, bl = _accumulate_flow_durations(get_issue_flow_timeline(issue), categorizer)
        total_active += act
        total_waiting += wt
        total_blocked += bl

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


def _collect_state_durations(issues, categorizer: FlowStateCategorizer):
    state_durations = {}
    state_active_issues = {}
    for issue in issues:
        timeline = get_issue_flow_timeline(issue)
        for t in timeline:
            state = t["state"]
            cat = categorizer.categorize_state(state)
            if cat in ["DONE", "To Do"]:
                continue
            duration = t["duration_seconds"] / 86400.0
            if state not in state_durations:
                state_durations[state] = []
                state_active_issues[state] = 0
            state_durations[state].append(duration)
        if not issue.resolved_at:
            curr_state = issue.status_actual
            state_active_issues[curr_state] = state_active_issues.get(curr_state, 0) + 1
    return state_durations, state_active_issues


def _format_bottleneck_results(state_durations, state_active_issues, total_all_durations):
    results = []
    for state, durations in state_durations.items():
        if not durations:
            continue
        durations.sort()
        count = len(durations)
        avg = sum(durations) / count
        if count >= 2:
            quantiles = statistics.quantiles(durations, n=100, method='inclusive')
            p50, p75, p95 = quantiles[49], quantiles[74], quantiles[94]
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


def detect_bottlenecks(db: Session, project_id: str, sprint_id: Optional[str] = None) -> List[Dict[str, Any]]:
    query = db.query(models.Issue).filter(models.Issue.id_proyecto == project_id)
    if sprint_id:
        query = query.filter(models.Issue.id_sprint == sprint_id)
        
    issues = query.all()
    categorizer = FlowStateCategorizer(db, project_id)
    state_durations, state_active_issues = _collect_state_durations(issues, categorizer)
    total_all_durations = sum(sum(durs) for durs in state_durations.values())
    return _format_bottleneck_results(state_durations, state_active_issues, total_all_durations)


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


def _calculate_issue_aging_seconds(timeline: List[Dict[str, Any]], categorizer: FlowStateCategorizer) -> tuple[bool, float]:
    started_processing = False
    total_seconds = 0.0
    for t in timeline:
        cat = categorizer.categorize_state(t["state"])
        if cat in ["ACTIVE", "WAITING", "BLOCKED"] and not started_processing:
            started_processing = True
        if started_processing:
            total_seconds += t["duration_seconds"]
    return started_processing, total_seconds


def get_aging_work(db: Session, project_id: str) -> List[Dict[str, Any]]:
    issues = db.query(models.Issue).filter(
        models.Issue.id_proyecto == project_id,
        models.Issue.resolved_at.isnot(None) == False
    ).all()
    
    categorizer = FlowStateCategorizer(db, project_id)
    aging_list = []
    
    for issue in issues:
        started, total_seconds = _calculate_issue_aging_seconds(get_issue_flow_timeline(issue), categorizer)
        if started and total_seconds > 0:
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


def _to_naive_utc(dt, now_dt):
    if dt is None:
        return now_dt
    if hasattr(dt, 'tzinfo') and dt.tzinfo is not None:
        return dt.astimezone(timezone.utc).replace(tzinfo=None)
    return dt


def _resolve_issue_state_at_day(issue, day_end, now_dt):
    issue_created = _to_naive_utc(issue.created_at, now_dt)
    if issue_created > day_end:
        return None
    timeline = get_issue_flow_timeline(issue)
    state_at_day = None
    for t in timeline:
        start = _to_naive_utc(t["start"], now_dt)
        end = _to_naive_utc(t["end"], now_dt)
        if start <= day_end and end >= day_end:
            state_at_day = t["state"]
            break
        elif end <= day_end:
            state_at_day = t["state"]
    return state_at_day


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
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    start_date = now - timedelta(days=30)

    for i in range(31):
        day = start_date + timedelta(days=i)
        day_end = day.replace(hour=23, minute=59, second=59)
        day_counts = {"To Do": 0, "Active": 0, "Waiting": 0, "Blocked": 0, "Done": 0}

        for issue in issues:
            state_at_day = _resolve_issue_state_at_day(issue, day_end, now)
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
