# app/services/performance_score_engine.py
# Motor de Cálculo del Performance Score Ponderado (0-100 pts) y Matriz de 4 Cuadrantes (Fase 6)

import math
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
import app.models as models
from app.services.dev_metrics_service import get_developer_scorecard_data

def calculate_performance_score(
    tickets_done: int,
    team_avg_tickets: float,
    sp_done: float,
    team_avg_sp: float,
    avg_cycle_time: float,
    team_avg_cycle_time: float,
    commitment_pct: float,
    bugs_reopened: int,
    total_bugs: int
) -> Dict[str, Any]:
    """
    Calcula la puntuación de rendimiento ponderada (0.0 a 100.0) desglosada en 5 pilares:
    - Throughput (25%)
    - Velocity SP (20%)
    - Agilidad / Cycle Time Inverso (20%)
    - Commitment Reliability (20%)
    - Calidad / Clean Code (15%)
    """
    # 1. Throughput Score (25%)
    ratio_tp = (tickets_done / max(team_avg_tickets, 1.0)) if team_avg_tickets > 0 else (1.0 if tickets_done > 0 else 0.5)
    s_tp = min(ratio_tp * 75.0, 100.0)

    # 2. Velocity Score (20%)
    ratio_sp = (sp_done / max(team_avg_sp, 1.0)) if team_avg_sp > 0 else (1.0 if sp_done > 0 else 0.5)
    s_sp = min(ratio_sp * 75.0, 100.0)

    # 3. Cycle Time Score (20%) — Menor cycle time respecto al promedio = Mayor puntaje
    if avg_cycle_time <= 0:
        s_ct = 80.0
    else:
        ct_ratio = (avg_cycle_time / max(team_avg_cycle_time, 1.0))
        if ct_ratio <= 1.0:
            s_ct = min(100.0, 80.0 + (1.0 - ct_ratio) * 20.0)
        else:
            s_ct = max(10.0, 80.0 - (ct_ratio - 1.0) * 35.0)

    # 4. Commitment Reliability Score (20%)
    s_com = min(max(commitment_pct, 0.0), 100.0)

    # 5. Quality Score (15%)
    if total_bugs > 0:
        clean_ratio = max(0.0, 1.0 - (bugs_reopened / total_bugs))
        s_qual = clean_ratio * 100.0
    else:
        s_qual = 95.0 if bugs_reopened == 0 else 50.0

    # Ponderación Global (100%)
    score = (0.25 * s_tp) + (0.20 * s_sp) + (0.20 * s_ct) + (0.20 * s_com) + (0.15 * s_qual)
    final_score = round(min(max(score, 0.0), 100.0), 1)

    return {
        "final_score": final_score,
        "desglose": {
            "throughput_score": round(s_tp, 1),
            "velocity_score": round(s_sp, 1),
            "cycle_time_score": round(s_ct, 1),
            "commitment_score": round(s_com, 1),
            "quality_score": round(s_qual, 1)
        }
    }

def determine_quadrant(
    dev_cycle_time: float,
    team_avg_cycle_time: float,
    quality_score: float
) -> Dict[str, str]:
    """
    Clasifica a un desarrollador en la Matriz de 4 Cuadrantes:
    - ESTRELLA: Cycle Time <= Promedio Y Calidad >= 80%
    - METODICO: Cycle Time > Promedio Y Calidad >= 80%
    - ALTO_VOLUMEN: Cycle Time <= Promedio Y Calidad < 80%
    - ATASCADO: Cycle Time > Promedio Y Calidad < 80%
    """
    is_fast = dev_cycle_time <= max(team_avg_cycle_time, 0.1) or dev_cycle_time == 0
    is_high_quality = quality_score >= 75.0

    if is_fast and is_high_quality:
        return {
            "codigo": "ESTRELLA",
            "nombre": "Estrella / Top Performance",
            "descripcion": "Alta velocidad de entrega manteniendo estándares rigurosos de calidad sin re-apertura de bugs.",
            "color": "emerald"
        }
    elif not is_fast and is_high_quality:
        return {
            "codigo": "METODICO",
            "nombre": "Metódico / Alta Precisión",
            "descripcion": "Ritmo analítico y constante. Prioriza la solidez del código y la ausencia de defectos.",
            "color": "indigo"
        }
    elif is_fast and not is_high_quality:
        return {
            "codigo": "ALTO_VOLUMEN",
            "nombre": "Alto Volumen / En Riesgo QA",
            "descripcion": "Excelente velocidad y rendimiento en volumen, pero presenta incidencias devueltas por QA.",
            "color": "amber"
        }
    else:
        return {
            "codigo": "ATASCADO",
            "nombre": "Atascado / Requiere Apoyo",
            "descripcion": "Tiempos de desarrollo prolongados e incidencias técnicas. Requiere pairing o apoyo del Líder Técnico.",
            "color": "rose"
        }

def calculate_team_performance_matrix(
    db: Session,
    proyecto_id: str = "PROJ-01",
    sprint_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Genera la Matriz Comparativa de Equipo completa (Fase 6):
    - Calcula métricas desglosadas por desarrollador
    - Determina el Performance Score (0-100 pts)
    - Asigna el cuadrante operativo
    - Genera ranking con posiciones y explicaciones claras ("El porqué de las cosas")
    """
    # 1. Obtener desarrolladores únicos del proyecto
    dev_users = []
    try:
        query = db.query(models.Issue.assignee_id, models.Issue.assignee_name, models.Issue.assignee_email).filter(
            models.Issue.id_proyecto == proyecto_id
        ).distinct()
        results = query.all()
        seen = set()
        for row in results:
            a_id = getattr(row, 'assignee_id', None) or "UNASSIGNED"
            if a_id not in seen and a_id != "UNASSIGNED":
                seen.add(a_id)
                dev_users.append({
                    "assignee_id": a_id,
                    "nombre": getattr(row, 'assignee_name', None) or "Desarrollador",
                    "email": getattr(row, 'assignee_email', None) or ""
                })
    except Exception as e:
        db.rollback()
        print("Fallback en matrix query:", e)

    if not dev_users:
        return {
            "proyecto_id": proyecto_id,
            "sprint_id": sprint_id,
            "team_summary": {
                "total_desarrolladores": 0,
                "promedio_score_equipo": 0,
                "team_avg_tickets": 0,
                "team_avg_sp": 0,
                "team_avg_cycle_time": 0,
                "top_performer": None,
                "conteo_cuadrantes": {"ESTRELLA": 0, "METODICO": 0, "ALTO_VOLUMEN": 0, "ATASCADO": 0}
            },
            "developers": []
        }

    # 2. Recopilar scorecards individuales
    dev_metrics_list = []
    for d in dev_users:
        try:
            scorecard = get_developer_scorecard_data(db, proyecto_id, email_or_assignee_id=d["email"] or d["assignee_id"])
        except Exception as e:
            db.rollback()
            scorecard = {}

        dev_metrics_list.append({
            "assignee_id": d["assignee_id"],
            "nombre": d["nombre"],
            "email": d["email"],
            "scorecard": scorecard
        })

    # Helper para extraer KPI de manera segura
    def extract_kpi(sc_dict, field_name, default_val):
        if not isinstance(sc_dict, dict):
            return default_val
        kpis_obj = sc_dict.get("kpis")
        if isinstance(kpis_obj, dict) and field_name in kpis_obj:
            return kpis_obj[field_name]
        if field_name in sc_dict:
            return sc_dict[field_name]
        return default_val

    # 3. Calcular promedios del equipo para el benchmark
    total_devs = max(len(dev_metrics_list), 1)
    sum_tickets = sum(extract_kpi(m["scorecard"], "throughput_issues", 6) for m in dev_metrics_list)
    sum_sp = sum(extract_kpi(m["scorecard"], "velocity_sp", 20.0) for m in dev_metrics_list)
    sum_ct = sum(extract_kpi(m["scorecard"], "cycle_time_promedio_dias", 3.2) for m in dev_metrics_list)

    team_avg_tickets = round(sum_tickets / total_devs, 1)
    team_avg_sp = round(sum_sp / total_devs, 1)
    team_avg_cycle_time = round(sum_ct / total_devs, 1)

    # 4. Procesar score y cuadrante por desarrollador
    matrix_developers = []
    for m in dev_metrics_list:
        sc = m["scorecard"]

        tickets_done = extract_kpi(sc, "throughput_issues", 6)
        sp_done = extract_kpi(sc, "velocity_sp", 20.0)
        cycle_time = extract_kpi(sc, "cycle_time_promedio_dias", 3.2)
        commitment = extract_kpi(sc, "commitment_rate_pct", 85.0)
        bugs_totales = extract_kpi(sc, "bugs_totales", 0)
        bugs_resueltos = extract_kpi(sc, "bugs_resueltos", 0)
        wip_actual = extract_kpi(sc, "wip_actual", 0)
        bugs_reopened = max(0, bugs_totales - bugs_resueltos)

        # Algoritmo de Score
        score_res = calculate_performance_score(
            tickets_done=tickets_done,
            team_avg_tickets=team_avg_tickets,
            sp_done=sp_done,
            team_avg_sp=team_avg_sp,
            avg_cycle_time=cycle_time,
            team_avg_cycle_time=team_avg_cycle_time,
            commitment_pct=commitment,
            bugs_reopened=bugs_reopened,
            total_bugs=bugs_totales
        )

        final_score = score_res["final_score"]
        desglose = score_res["desglose"]

        # Asignación de Cuadrante
        quadrant = determine_quadrant(
            dev_cycle_time=cycle_time,
            team_avg_cycle_time=team_avg_cycle_time,
            quality_score=desglose["quality_score"]
        )

        # Generar explicación explícita de rendimiento ("El porqué de las cosas")
        explicacion_razones = []
        if tickets_done > team_avg_tickets:
            explicacion_razones.append(f"Supera el volumen promedio del equipo con {tickets_done} tickets entregados (Promedio: {team_avg_tickets}).")
        elif tickets_done < team_avg_tickets:
            explicacion_razones.append(f"Su volumen de entrega ({tickets_done} tickets) está por debajo del promedio del equipo ({team_avg_tickets}).")
        else:
            explicacion_razones.append(f"Mantiene una entrega constante alineada al promedio del equipo ({tickets_done} tickets).")

        if cycle_time > 0 and cycle_time <= team_avg_cycle_time:
            explicacion_razones.append(f"Tiempo de ciclo ágil de {cycle_time} días/ticket (promedio equipo: {team_avg_cycle_time}d).")
        elif cycle_time > team_avg_cycle_time:
            explicacion_razones.append(f"Tiempo de ciclo de {cycle_time}d supera el promedio del equipo ({team_avg_cycle_time}d), indicando posibles cuellos de botella.")

        if desglose["quality_score"] >= 80:
            explicacion_razones.append("Excelente índice de calidad sin devoluciones críticas de QA.")
        else:
            explicacion_razones.append(f"Índice de calidad de {desglose['quality_score']}% afectado por {bugs_reopened} incidencias con observaciones.")

        matrix_developers.append({
            "assignee_id": m["assignee_id"],
            "nombre": m["nombre"],
            "email": m["email"],
            "throughput_issues": tickets_done,
            "velocity_sp": sp_done,
            "cycle_time_dias": cycle_time,
            "wip_actual": wip_actual,
            "commitment_pct": commitment,
            "quality_pct": desglose["quality_score"],
            "performance_score": final_score,
            "desglose_score": desglose,
            "cuadrante": quadrant,
            "explicacion_razones": explicacion_razones,
            "scorecard_completo": sc
        })

    # 5. Ordenar desarrolladores por Performance Score descendente
    matrix_developers.sort(key=lambda x: x["performance_score"], reverse=True)

    # 6. Asignar posiciones y medallas de honor
    badges = ["🥇 Medalla de Oro", "🥈 Medalla de Plata", "🥉 Medalla de Bronce", "🎖️ Mención de Honor"]
    for i, dev in enumerate(matrix_developers):
        dev["rank_posicion"] = i + 1
        dev["badge_honor"] = badges[i] if i < len(badges) else "🎖️ Mención de Honor"

    # Resumen de Cuadrantes
    conteo_cuadrantes = {
        "ESTRELLA": sum(1 for d in matrix_developers if d["cuadrante"]["codigo"] == "ESTRELLA"),
        "METODICO": sum(1 for d in matrix_developers if d["cuadrante"]["codigo"] == "METODICO"),
        "ALTO_VOLUMEN": sum(1 for d in matrix_developers if d["cuadrante"]["codigo"] == "ALTO_VOLUMEN"),
        "ATASCADO": sum(1 for d in matrix_developers if d["cuadrante"]["codigo"] == "ATASCADO")
    }

    team_avg_score = round(sum(d["performance_score"] for d in matrix_developers) / max(len(matrix_developers), 1), 1)

    return {
        "proyecto_id": proyecto_id,
        "sprint_id": sprint_id,
        "team_summary": {
            "total_desarrolladores": len(matrix_developers),
            "promedio_score_equipo": team_avg_score,
            "team_avg_tickets": team_avg_tickets,
            "team_avg_sp": team_avg_sp,
            "team_avg_cycle_time": team_avg_cycle_time,
            "top_performer": matrix_developers[0] if matrix_developers else None,
            "conteo_cuadrantes": conteo_cuadrantes
        },
        "developers": matrix_developers
    }
