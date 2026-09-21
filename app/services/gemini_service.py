# app/services/gemini_service.py
# Servicio de Inteligencia Artificial Generativa impulsado por Google Gemini API (gemini-2.5-flash)
# Proporciona diagnósticos analíticos en tiempo real para:
# 1. AI Dev Coach (Mascota Búho en la vista de Desarrollador)
# 2. Dashboard del Planificador (Salud del sprint y alertas de cuellos de botella)
# 3. Informes Ejecutivos PDF (Conclusiones analíticas consolidadas)

import json
import httpx
from typing import Dict, Any, List, Optional
from app.core.config import GEMINI_API_KEY, GEMINI_MODEL_NAME
from app.core.cache import ShortLivedCache

# Caché en memoria de 5 minutos (300 segundos) para evitar agotar cuotas y acelerar respuestas
gemini_cache = ShortLivedCache(ttl_seconds=300)

GEMINI_API_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models"


def is_gemini_configured() -> bool:
    """Verifica si la API Key de Gemini está presente en la configuración."""
    return bool(GEMINI_API_KEY and len(GEMINI_API_KEY) > 10)


def _call_gemini_rest_api(prompt: str, temperature: float = 0.4, max_tokens: int = 350) -> Optional[str]:
    """
    Realiza una petición HTTP directa a la API REST de Google Gemini.
    Prueba el modelo configurado (gemini-3.6-flash) y conmuta automáticamente si Google exige otro modelo.
    """
    if not is_gemini_configured():
        return None

    primary_model = GEMINI_MODEL_NAME or "gemini-flash-lite-latest"
    candidate_models = [primary_model, "gemini-flash-lite-latest", "gemini-flash-latest", "gemini-2.5-flash-lite"]

    payload = {
        "contents": [
            {
                "parts": [
                    {"text": prompt}
                ]
            }
        ],
        "generationConfig": {
            "temperature": temperature,
            "maxOutputTokens": max_tokens
        }
    }

    with httpx.Client(timeout=25.0) as client:
        for model in candidate_models:
            url = f"{GEMINI_API_ENDPOINT}/{model}:generateContent?key={GEMINI_API_KEY}"
            try:
                response = client.post(url, json=payload)
                if response.status_code == 200:
                    res_data = response.json()
                    candidates = res_data.get("candidates", [])
                    if candidates:
                        parts = candidates[0].get("content", {}).get("parts", [])
                        if parts and "text" in parts[0]:
                            return parts[0]["text"].strip()
                elif response.status_code == 404:
                    print(f"Modelo Gemini '{model}' no disponible (404), intentando siguiente modelo candidato...")
                    continue
                else:
                    print(f"Aviso Gemini API ({model} HTTP {response.status_code}): {response.text[:200]}")
            except Exception as e:
                print(f"Error conectando con Google Gemini API ({model}): {e}")

    return None


def generate_dev_coach_tip(scorecard: dict, urgent_qa: list, active_dev: list, fallback_tip: str) -> str:
    """
    Genera un consejo inteligente y empático de NubI IA (Mascota Búho) impulsado por Gemini.
    Usa caché por desarrollador de 5 minutos. Si falla o no hay API Key, retorna fallback_tip.
    """
    dev_email = scorecard.get("email") or scorecard.get("assignee_name") or "dev_default"
    cache_key = f"gemini_dev_tip_{dev_email}"
    cached = gemini_cache.get(cache_key)
    if cached:
        return cached

    if not is_gemini_configured():
        return fallback_tip

    ct = scorecard.get("cycle_time_personal", 0)
    ct_prev = scorecard.get("cycle_time_prev", 0)
    wip = scorecard.get("wip_tickets", 0)
    completed = scorecard.get("throughput_tickets", 0)
    clean_pct = scorecard.get("clean_deliveries_pct", 100)

    qa_bugs_str = ", ".join([b.get("key_issue", "") for b in urgent_qa[:3]]) if urgent_qa else "Ninguno"

    prompt = f"""
Eres 'NubI IA', la Inteligencia Artificial y Asistente Analítico de MCHAV Analytics (representado por una mascota búho sabia y experta en agilidad).
Tu misión es darle un consejo conciso, empático y constructivo a un desarrollador sobre su rendimiento actual.

Datos reales del desarrollador:
- Tiempo de ciclo (Cycle Time) actual: {ct} días vs sprint anterior: {ct_prev} días.
- Tareas simultáneas en progreso (WIP): {wip} tareas.
- Entregas completadas en este sprint: {completed} tickets.
- Porcentaje de entregas sin reabrir bugs: {clean_pct}%.
- Bugs prioritarios en QA pendientes: {qa_bugs_str}.

Reglas de respuesta:
1. Responde en español en exactamente 2 o 3 frases directas y motivadoras.
2. Comienza reconociendo un logro positivo o una oportunidad clara de mejora.
3. Si hay WIP alto (>3) o bugs en QA, dale prioridad a sugerir cerrar tareas o apoyar en QA.
4. Mantén un tono profesional pero muy cálido de coach tecnológico. No uses viñetas ni títulos, solo el párrafo fluido.
"""

    gemini_text = _call_gemini_rest_api(prompt, temperature=0.5, max_tokens=250)
    if gemini_text:
        gemini_cache.set(cache_key, gemini_text)
        return gemini_text

    return fallback_tip


def generate_lider_dashboard_insights(sprint_health: dict, alerts: list, fallback_insights: dict) -> dict:
    """
    Genera diagnósticos analíticos ejecutivos para el Dashboard del Planificador impulsados por Gemini.
    """
    proj_id = sprint_health.get("id_proyecto", "PROJ-01")
    cache_key = f"gemini_lider_insights_{proj_id}"
    cached = gemini_cache.get(cache_key)
    if cached:
        return cached

    if not is_gemini_configured():
        return fallback_insights

    commitment = sprint_health.get("commitment_reliability_pct", 0)
    scope_creep = sprint_health.get("scope_creep_sp", 0)
    flow_eff = sprint_health.get("flow_efficiency_pct", 0)
    health_score = sprint_health.get("health_score", 0)
    alert_count = len(alerts)

    prompt = f"""
Eres el consultor senior de agilidad e IA de MCHAV Analytics. Genera un diagnóstico ejecutivo para el Planificador.

Métricas del Proyecto ({proj_id}):
- Salud Global del Sprint: {health_score}/100 pts.
- Cumplimiento del Compromiso (Commitment Reliability): {commitment}%.
- Alcance agregado (Scope Creep): +{scope_creep} Story Points.
- Eficiencia de Flujo: {flow_eff}%.
- Alertas activas de cuellos de botella: {alert_count} alertas.

Devuelve un JSON strictly válido con la siguiente estructura (sin comillas de código markdown extra):
{{
  "diagnostico_ejecutivo": "2 frases con la evaluación técnica general de la velocidad y salud.",
  "principal_riesgo": "1 frase detallando el mayor riesgo detectado en el sprint.",
  "recomendacion_lider": "1 frase con la acción prioritaria para el Scrum Master o Planificador."
}}
"""

    raw_json = _call_gemini_rest_api(prompt, temperature=0.3, max_tokens=300)
    if raw_json:
        try:
            # Limpiar posibles bloques markdown ```json ... ```
            cleaned_str = raw_json.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(cleaned_str)
            gemini_cache.set(cache_key, parsed)
            return parsed
        except Exception:
            pass

    return fallback_insights


def generate_pdf_conclusions(proyecto_nombre: str, avg_cycle_time: float, throughput: int, velocity: float) -> str:
    """
    Genera el bloque de conclusiones ejecutivas impulsadas por Gemini para el informe PDF.
    """
    if not is_gemini_configured():
        return (
            f"El proyecto '{proyecto_nombre}' muestra una entrega sostenida con un tiempo de ciclo promedio de {avg_cycle_time} días "
            f"y una velocidad de {velocity} Story Points. Se recomienda mantener el enfoque en la reducción del WIP."
        )

    prompt = f"""
Escribe una conclusión ejecutiva en español (máximo 4 renglones) para un reporte PDF oficial sobre el proyecto '{proyecto_nombre}'.
Métricas:
- Tiempo de ciclo promedio: {avg_cycle_time} días.
- Rendimiento (Throughput): {throughput} tickets resueltos.
- Velocidad: {velocity} Story Points completados.

Usa un tono formal, analítico y corporativo de nivel C-Level.
"""

    res = _call_gemini_rest_api(prompt, temperature=0.3, max_tokens=200)
    if res:
        return res

    return (
        f"El proyecto '{proyecto_nombre}' muestra una entrega sostenida con un tiempo de ciclo promedio de {avg_cycle_time} días "
        f"y una velocidad de {velocity} Story Points. Se recomienda mantener el enfoque en la reducción del WIP."
    )


def generar_analisis_ejecutivo_nubi(context_info: str) -> str:
    """Genera un análisis ejecutivo corto para correos mensuales utilizando Gemini o fallback."""
    if not is_gemini_configured():
        return (
            "Durante este período el equipo ha mantenido un ritmo constante de entregas. "
            "Se recomienda mantener historias de usuario desglosadas en tamaños no mayores a 8 SP "
            "para optimizar el flujo continuo y reducir tiempos en progreso."
        )
    
    prompt = f"""
Actúa como NubI IA, consultor senior de agilidad de MCHAV Analytics.
Genera un diagnóstico ejecutivo breve (máximo 3 frases) en español para el reporte por correo.
Métricas clave: {context_info}
Responde en un párrafo profesional y conciso.
"""
    res = _call_gemini_rest_api(prompt, temperature=0.3, max_tokens=150)
    if res:
        return res
    return (
        "Durante este período el equipo ha mantenido un ritmo constante de entregas. "
        "Se recomienda mantener historias de usuario desglosadas en tamaños no mayores a 8 SP "
        "para optimizar el flujo continuo y reducir tiempos en progreso."
    )



def chat_with_gemini(user_message: str, context_info: dict = None, conversation_history: list = None) -> str:
    """
    Mantiene una conversación analítica, fluida e inteligente con el usuario basada en datos reales de MCHAV y Jira.
    Soporta desglose por desarrollador individual, cuellos de botella, salud de sprint y alertas.
    """
    if not is_gemini_configured():
        return (
            "🤖 *Modo Conversacional Local*: No he detectado una `GEMINI_API_KEY` activa en el archivo `.env`. "
            "Para chatear en tiempo real con la IA de Google Gemini, configura tu API Key en el `.env` del backend."
        )

    context_info = context_info or {}
    user_name = context_info.get("user_name", "Usuario")
    proj_id = context_info.get("id_proyecto", "PROJ-01")
    
    # Formatear la lista de desarrolladores individualmente
    devs_data = context_info.get("desempeno_desarrolladores_individual", [])
    devs_str = json.dumps(devs_data, indent=2, ensure_ascii=False) if devs_data else "No hay métricas de desarrolladores registradas aún."
    
    # Formatear salud de sprint y cuellos de botella
    salud_str = json.dumps(context_info.get("salud_sprint", {}), indent=2, ensure_ascii=False)
    blocked_str = json.dumps(context_info.get("tickets_bloqueados_o_criticos", []), indent=2, ensure_ascii=False)
    alerts_str = json.dumps(context_info.get("alertas_recientes", []), indent=2, ensure_ascii=False)

    history_str = ""
    if conversation_history:
        for msg in conversation_history[-6:]: # Últimos 6 mensajes
            role = "Usuario" if msg.get("sender") == "user" else "NubI IA"
            history_str += f"{role}: {msg.get('text', '')}\n"

    prompt = f"""
Eres 'NubI IA', la Inteligencia Artificial Generativa y Senior Agile Data Scientist de MCHAV Analytics. Eres un experto analista de datos de software, ingeniería de procesos ágiles y rendimiento técnico de equipos de desarrollo.

TU OBJETIVO: Proveer diagnósticos profundos, altamente analíticos, estructurados y precisos basados en los DATOS REALES EXTRAÍDOS DE LA BASE DE DATOS Y JIRA.

=== DATOS ANALÍTICOS REALES EXTRAÍDOS DE LA BASE DE DATOS Y JIRA ===

1. DESEMPEÑO INDIVIDUAL POR DESARROLLADOR:
{devs_str}

2. SALUD DEL SPRINT Y FLUJO OPERATIVO:
{salud_str}

3. INCIDENCIAS CRÍTICAS Y ESTANCADAS:
{blocked_str}

4. ALERTAS OPERATIVAS RECIENTES DEL SISTEMA:
{alerts_str}

=== FIN DE DATOS DE LA BASE DE DATOS ===

HISTORIAL RECIENTE DE CONVERSACIÓN:
{history_str}

PREGUNTA DEL USUARIO ({user_name}):
"{user_message}"

INSTRUCCIONES DE RESPUESTA Y ANÁLISIS:
1. SI EL USUARIO PREGUNTA SOBRE DESEMPEÑO DE DESARROLLADORES, RENDIMIENTO INDIVIDUAL O INTEGRANTES DEL EQUIPO:
   - Menciona a CADA desarrollador por su NOMBRE real registrado en los datos.
   - Detalla sus Story Points entregados, su Cycle Time promedio en días, su nivel de WIP (tareas en progreso) y los bugs asignados.
   - Ofrece una evaluación crítica constructiva individual para cada uno (ej. quién tiene el ritmo de entrega más ágil, quién tiene sobrecarga de WIP o bloqueos).
2. SI EL USUARIO PREGUNTA SOBRE SALUD DEL SPRINT, KPIS O CUELLOS DE BOTELLA:
   - Cita el puntaje exacto de salud (Health Score), el % de cumplimiento de compromisos y la desviación por alcance (Scope Creep).
   - Identifica las fases bloqueantes y menciona las claves de los tickets específicos (ej. MCHAV-101, MCHAV-105).
3. ESTRUCTURA Y FORMATO DE LA RESPUESTA:
   - Usa un formato Markdown pulido con encabezados, listas con viñetas, negritas para números clave y tablas si facilitan la comparación.
   - Incluye emojis sutiles (🦉, 📊, ⚡, 🎯, 💡, ⚠️).
   - Provee SIEMPRE recomendaciones de acción concretas al final para optimizar el flujo.
   - Sé exhaustivo, analítico y profesional. No des respuestas genéricas de 2 líneas.
"""

    reply = _call_gemini_rest_api(prompt, temperature=0.4, max_tokens=1200)
    if reply:
        return reply

    return "Disculpa, en este momento no pude obtener respuesta del motor analítico de Gemini. Por favor verifica tu conexión o intenta nuevamente."

def _build_proyecto_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    return f"""
Actúa como un Agile Coach experto evaluando la salud general del proyecto.
Tu objetivo es evaluar el desempeño global basándote en métricas reales.
No uses formato de 'plantilla de IA'. Escribe párrafos fluidos, analíticos y directos.
Métricas del proyecto:
- Velocidad: {v} Story Points completados.
- Rendimiento (Throughput): {t} tickets completados.
- Tiempo de ciclo promedio: {ct} días.
- Días bloqueados acumulados: {bd} días.
- Bugs reportados: {bugs}.
- Alcance total: {scope} Story Points.
- Sprint Health Score promedio: {health}/100.
- P50: {p50} días, P85: {p85} días, P95: {p95} días.
- Porcentaje de completitud: {pct}%.

ESTRUCTURA ESTRICTA DE CADA SECCIÓN (OBLIGATORIO):
El sistema separa el reporte usando etiquetas '[PROYECTO_X] TITULO'.

LAS 4 SECCIONES A DESARROLLAR (Debes incluir EXACTAMENTE estas 4 en este orden):

[PROYECTO_1] CONTEXTO GENERAL DEL PERIODO
  - Escribe un párrafo evaluando el rendimiento global del proyecto.
  
[PROYECTO_2] ESTADO DEL FLUJO DE TRABAJO Y CUELLOS DE BOTELLA
  - Análisis detallado del cycle time, throughput y días de bloqueo en un párrafo fluido.

[PROYECTO_3] ANÁLISIS DE PREDICTIBILIDAD Y RIESGOS
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_BURNUP]
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_VELOCIDAD]
  - Basado en los percentiles P50/P85/P95, evalúa qué tan predecible es la entrega del proyecto.
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_FLUJO]

[PROYECTO_4] CONCLUSIONES ESTRATÉGICAS Y PLAN DE ACCIÓN
  - Conclusiones fluidas y pasos accionables recomendados para el liderazgo técnico.
"""

def _build_desarrollador_prompt(metrics, v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    import json
    history = metrics.get('history_data', [])
    history_str = json.dumps(history, indent=2) if history else 'Sin historial'
    dev_name = metrics.get('developerName') or 'el desarrollador'
    
    return f"""
Actúa como un Tech Lead analítico evaluando a {dev_name}.
Tu objetivo es evaluar el desempeño de este desarrollador basándote en métricas personales reales.
No uses formato de 'plantilla de IA'. Escribe párrafos fluidos y profesionales (evita saludos coloquiales como 'Hola a todos', ve directo al análisis).

=== HISTORIAL RECIENTE ===
{history_str}
==========================

ESTRUCTURA ESTRICTA DE CADA SECCIÓN (OBLIGATORIO):
El sistema UI separa el reporte usando etiquetas '# 0X — TITULO'.
1. TITULO EN FORMATO H1 (# 0X — NOMBRE EN MAYUSCULAS).
2. ANALISIS FLUIDO.

LAS 4 SECCIONES A DESARROLLAR (Debes incluir EXACTAMENTE estas 4 en este orden):

# 01 — PERFIL DE DESEMPEÑO
  - Escribe un párrafo inicial directo y profesional resumiendo el estado general de {dev_name}.
  - Inmediatamente después, inyecta OBLIGATORIAMENTE la etiqueta: [TABLA_EVOLUCION]
  - Luego, redacta un párrafo analizando su evolución histórica basada en la tabla.

# 02 — ACTIVIDAD Y ENTREGA
  - Escribe un breve párrafo analizando su throughput, la cantidad de bugs introducidos, y los puntos entregados.
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_VELOCIDAD]
  - Y con un cierre analítico de los datos.

# 03 — FLUJO Y PRODUCTIVIDAD
  - Escribe un análisis profundo de su ritmo y bloqueos.
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_FLUJO]

# 04 — DIAGNÓSTICO Y PLAN DE MEJORA
  - Basado en los datos técnicos, define de 2 a 3 hallazgos clave y un plan de acción sugerido para el desarrollador.
"""

def _build_general_prompt(metrics):
    proj_metrics = metrics.get('projectMetrics', [])
    total_sp = metrics.get('velocity', 0)
    total_tickets = metrics.get('throughput', 0)
    
    proyectos_texto = ""
    for p in proj_metrics:
        proyectos_texto += f"- Proyecto: {p.get('projectName')}, SP Completados: {p.get('velocity')}, Tickets: {p.get('throughput')}, Cycle Time: {p.get('cycleTime')} días, Bloqueos: {p.get('blockedDays')} días, Bugs: {p.get('bugs')}\n"
    
    return f"""
Actúa como un Director de Ingeniería (VP of Engineering) evaluando un portafolio de múltiples proyectos.
Genera un "Informe Ejecutivo de Rendimiento" consolidado. 
El tono debe ser fluido, analítico, altamente gerencial, directo, estratégico y basado en datos empíricos.
No uses formato de 'plantilla de IA'. Evita saludos, inicia inmediatamente con el reporte narrativo.

Datos Agregados del Portafolio:
- Total Story Points Entregados: {total_sp}
- Total Tickets Completados: {total_tickets}

Desglose por Proyectos:
{proyectos_texto}

ESTRUCTURA ESTRICTA DE CADA SECCIÓN (OBLIGATORIO):
El sistema separa el reporte usando etiquetas '# 0X — TITULO'.
1. TITULO EN FORMATO H1 (# 0X — TITULO).
2. ANALISIS FLUIDO.

LAS 3 SECCIONES A DESARROLLAR (Debes incluir EXACTAMENTE estas 3 en este orden):

# 01 — RESUMEN EJECUTIVO DEL PORTAFOLIO
  - Un párrafo resumiendo de manera fluida el desempeño agregado de los proyectos seleccionados.
  - Inmediatamente después, inyecta OBLIGATORIAMENTE la etiqueta: [TABLA_PORTAFOLIO]
  - Luego, redacta un párrafo destacando qué proyectos lideran la entrega y cuáles presentan mayores riesgos (bugs o bloqueos).

# 02 — RENDIMIENTO COMPARATIVO
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_PORTAFOLIO_VELOCIDAD]
  - Analiza de forma discursiva y analítica la distribución de Story Points entre los diferentes proyectos. ¿Está equilibrada la entrega de valor?

# 03 — CONCLUSIONES Y RIESGOS ESTRATÉGICOS
  - Redacta de 2 a 3 párrafos de conclusiones ejecutivas sobre la salud de estos proyectos, cuellos de botella observados y recomendaciones de mejora estructural.
"""

def generate_report_insights(metrics: dict, fallback: dict, report_type: str = "sprint", is_leader: bool = False) -> str:
    if not is_gemini_configured():
        return _get_fallback_insights(report_type)

    if is_leader:
        v = metrics.get("velocity", 0)
        t = metrics.get("throughput", 0)
        ct = metrics.get("cycleTime", 0)
        bd = metrics.get("blockedDays", 0)
        bugs = metrics.get("bugs", 0)
        scope = metrics.get("scope", 0)
        health = metrics.get("sprintHealth", 0)
        p50 = metrics.get("p50", 0)
        p85 = metrics.get("p85", 0)
        p95 = metrics.get("p95", 0)
        planned = metrics.get("planned", 0)
        pct = metrics.get("completionPct", 0)

        if report_type == "general":
            prompt = _build_lider_general_prompt(metrics)
        elif report_type == "desarrollador":
            prompt = _build_lider_desarrollador_prompt(metrics, v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct)
        elif report_type == "proyecto":
            prompt = _build_lider_proyecto_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct)
        else:
            prompt = _build_lider_sprint_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct)
    elif report_type == "general":
        prompt = _build_general_prompt(metrics)
    elif report_type == "desarrollador":
        v = metrics.get("velocity", 0)
        t = metrics.get("throughput", 0)
        ct = metrics.get("cycleTime", 0)
        bd = metrics.get("blockedDays", 0)
        bugs = metrics.get("bugs", 0)
        scope = metrics.get("scope", 0)
        health = metrics.get("sprintHealth", 0)
        p50 = metrics.get("p50", 0)
        p85 = metrics.get("p85", 0)
        p95 = metrics.get("p95", 0)
        planned = metrics.get("planned", 0)
        pct = metrics.get("completionPct", 0)
        prompt = _build_desarrollador_prompt(metrics, v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct)
    elif report_type == "proyecto":
        v = metrics.get("velocity", 0)
        t = metrics.get("throughput", 0)
        ct = metrics.get("cycleTime", 0)
        bd = metrics.get("blockedDays", 0)
        bugs = metrics.get("bugs", 0)
        scope = metrics.get("scope", 0)
        health = metrics.get("sprintHealth", 0)
        p50 = metrics.get("p50", 0)
        p85 = metrics.get("p85", 0)
        p95 = metrics.get("p95", 0)
        planned = metrics.get("planned", 0)
        pct = metrics.get("completionPct", 0)
        prompt = _build_proyecto_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct)
    else:
        v = metrics.get("velocity", 0)
        t = metrics.get("throughput", 0)
        ct = metrics.get("cycleTime", 0)
        bd = metrics.get("blockedDays", 0)
        bugs = metrics.get("bugs", 0)
        scope = metrics.get("scope", 0)
        health = metrics.get("sprintHealth", 0)
        p50 = metrics.get("p50", 0)
        p85 = metrics.get("p85", 0)
        p95 = metrics.get("p95", 0)
        planned = metrics.get("planned", 0)
        pct = metrics.get("completionPct", 0)
        prompt = _build_sprint_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct)

    reply = _call_gemini_rest_api(prompt, temperature=0.7, max_tokens=2500)
    if reply:
        return reply

    return _get_fallback_insights(report_type)

def _build_lider_sprint_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    spillover = max(0, planned - v)
    return f"""
Actúa como Nubi IA, Asistente Analítico del Líder Técnico y Facilitador Ágil.
Analiza el sprint con los siguientes datos empíricos:
Velocidad entregada: {v} SP (de {planned} SP planificados, {pct}% de cumplimiento). Throughput: {t} tickets cerrados. Stories/tareas en deuda (Spillover): {spillover} SP.
Cycle Time medio: {ct} días hábiles (descontando fines de semana y festivos). Bloqueos acumulados: {bd} días. Defectos: {bugs} bugs. Salud del Sprint: {health}/100.

REGLAS OBLIGATORIAS DE TONO Y ESTILO:
1. Utiliza un tono estrictamente constructivo, técnico y facilitador de equipo.
2. PROHIBIDO usar jerga imprecisa como 'con creces'. Reemplázala por porcentajes exactos e indicadores cuantitativos.
3. PROHIBIDO invocar 'intervención gerencial', 'intervención ejecutiva' o palabras que infundan temor o nerviosismo en el equipo.
4. Integra referencias directas a las gráficas (ejemplo: 'Como se observa en la banda verde/azul del Diagrama de Flujo CFD...').

Estructura el informe narrativo en 4 secciones continuas:

# 01 — DIAGNÓSTICO DE SALUD Y AVANCE LOGRADO
  - Describe el avance del sprint: salud ({health}/100), {v} SP completados ({pct}% del compromiso) y {t} tickets entregados frente a {spillover} SP que quedaron en deuda.

# 02 — EVOLUCIÓN DEL COMPROMISO Y METODOLOGÍA
  - Analiza cómo evolucionó el ritmo de entrega durante los días hábiles del sprint.

# 03 — CUELLOS DE BOTELLA Y LOCALIZACIÓN DEL PROBLEMA
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_FLUJO]
  - Analiza las causas de los {bd} días bloqueados y la concentración de tareas en revisión en el CFD, cuantificando las horas de retraso estimadas y el impacto de la multitarea.

# 04 — GUÍA DE ACOMPAÑAMIENTO Y PLAN TÁCTICO DEL LÍDER
  - Proporciona 3 acciones prácticas para que el Líder Técnico y el equipo rebalanceen el WIP y remuevan bloqueos en el próximo sprint.
"""

def _build_lider_proyecto_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    spillover = max(0, planned - v)
    return f"""
Actúa como Nubi IA, Asistente Analítico del Líder Técnico y Facilitador Ágil.
Analiza el proyecto con los datos:
Velocidad entregada: {v} SP. Throughput: {t} tickets resueltos. Tareas en deuda: {spillover} SP. Cycle Time medio: {ct} días hábiles (descontando fines de semana). Días bloqueados: {bd}. Bugs: {bugs}.

REGLAS OBLIGATORIAS DE TONO Y ESTILO:
1. Utiliza un tono constructivo, de soporte y enfocado en la mejora continua del equipo.
2. PROHIBIDO usar palabras vagas como 'con creces' o apelaciones a 'intervención gerencial/ejecutiva'.
3. Apóyate en métricas cuantitativas precisas y citas directas a las gráficas.

Estructura el informe narrativo en 4 secciones:

# 01 — CONTEXTO OPERATIVO Y SALUD DEL PROYECTO
  - Resumen del periodo: Sprints evaluados, {t} tareas resueltas, {v} SP completados y {spillover} SP pendientes.

# 02 — TENDENCIA DE VELOCIDAD E HISTÓRICO DE ENTREGAS
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_VELOCIDAD]
  - Cita la gráfica de velocidad explicando la evolución del rendimiento por sprint y la estabilidad de entregas.

# 03 — DIAGNÓSTICO DE FLUJO Y PUNTOS DE FRICCIÓN
  - Analiza la acumulación de trabajo en progreso (WIP), los {bd} días bloqueados y el impacto del trabajo simultáneo por desarrollador.

# 04 — HOJA DE RUTA Y ACCIONES TÁCTICAS DEL LÍDER
  - 3 recomendaciones prácticas para optimizar el ciclo de vida y proteger la capacidad del equipo.
"""

def _build_lider_desarrollador_prompt(metrics, v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    return f"""
Actúa como Nubi IA, Asistente Analítico del Líder Técnico.
Analiza la actividad del desarrollador con los datos:
Story Points completados: {v} SP. Tareas cerradas: {t}. Cycle Time personal: {ct} días hábiles. Días de bloqueo: {bd}. Bugs reabiertos: {bugs}.

REGLAS DE TONO: Tono positivo, de coaching técnico y crecimiento profesional. Cero lenguaje punitivo o jerárquico.

Estructura la evaluación narrativa en 4 secciones:

# 01 — PERFIL Y CARGA DE TRABAJO ACTUAL
  - Resumen de entregas cerradas ({t} tareas, {v} SP) y nivel de enfoque en el periodo.

# 02 — RITMO DE ENTREGA Y EVOLUCIÓN
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_VELOCIDAD]
  - Analiza la estabilidad de velocidad individual a lo largo de los sprints.

# 03 — IDENTIFICACIÓN DE IMPEDIMENTOS Y MULTITAREA
  - Evalúa la presencia de sobrecarga por WIP simultáneo, cuellos de botella en QA o días bloqueados ({bd} días).

# 04 — PLAN DE ACOMPAÑAMIENTO Y MENTORÍA TÉCNICA
  - Recomendaciones para el Líder Técnico sobre cómo apoyar al desarrollador, despejar bloqueos y balancear sus asignaciones.
"""

def _build_lider_general_prompt(metrics):
    return f"""
Actúa como Nubi IA, Asistente Analítico del Líder Técnico.
Analiza el portafolio consolidado del Líder con los datos:
Velocidad total: {metrics.get('velocity', 0)} SP. Throughput acumulado: {metrics.get('throughput', 0)} tickets. Cycle Time medio: {metrics.get('cycleTime', 0)} días hábiles. Bloqueos acumulados: {metrics.get('blockedDays', 0)} días.

REGLAS DE TONO: Tono constructivo de coordinación táctica multi-proyecto.

Estructura el informe en 4 secciones:

# 01 — VISIÓN CONSOLIDADA DEL PORTAFOLIO DE PROYECTOS
  - Resumen del estado global de los proyectos asignados y volumen acumulado de entregas.

# 02 — DESEMPEÑO COMPARATIVO DE LOS PROYECTOS
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_PORTAFOLIO_VELOCIDAD]
  - Analiza la velocidad y el ritmo comparativo entre proyectos.

# 03 — ANÁLISIS DE IMPEDIMENTOS Y BALANCE DE CAPACIDAD
  - Identifica cuellos de botella y concentración de bloqueos por proyecto.

# 04 — PRIORIZACIÓN SEMANAL Y ACCIONES DEL LÍDER
  - Guía táctica para redistribuir capacidad del equipo y mitigar riesgos en la próxima semana.
"""

def _get_fallback_insights(report_type: str) -> str:
    if report_type == "general":
        return """# 01 — RESUMEN EJECUTIVO DEL PORTAFOLIO\nAnálisis de IA no disponible en este momento.\n\n[TABLA_PORTAFOLIO]\n\n# 02 — RENDIMIENTO COMPARATIVO\n[GRAFICA_PORTAFOLIO_VELOCIDAD]\n### Análisis de entrega\nAnálisis de IA no disponible.\n\n# 03 — CONCLUSIONES Y RIESGOS ESTRATÉGICOS\nAnálisis de IA no disponible.\n"""
    elif report_type == "desarrollador":
        return """# 01 — PERFIL DE DESEMPEÑO\nAnálisis de IA no disponible.\n\n[TABLA_EVOLUCION]\n\n# 02 — ACTIVIDAD Y ENTREGA\n[GRAFICA_VELOCIDAD]\n### Análisis de distribución\nAnálisis de IA no disponible.\n\n# 03 — FLUJO Y PRODUCTIVIDAD\n[GRAFICA_FLUJO]\n### Lectura del flujo\nAnálisis de IA no disponible.\n\n# 04 — DIAGNÓSTICO Y PLAN DE MEJORA\n### Hallazgos clave\nAnálisis de IA no disponible.\n"""
    elif report_type == "proyecto":
        return """[PROYECTO_1] CONTEXTO GENERAL DEL PERIODO\nAnálisis de IA no disponible.\n[PROYECTO_2] ESTADO DEL FLUJO DE TRABAJO Y CUELLOS DE BOTELLA\nAnálisis de IA no disponible.\n[PROYECTO_3] ANÁLISIS DE PREDICTIBILIDAD Y RIESGOS\nAnálisis de IA no disponible.\n[PROYECTO_4] CONCLUSIONES ESTRATÉGICAS Y PLAN DE ACCIÓN\nAnálisis de IA no disponible.\n"""
        return """# 01 — CONTEXTO GENERAL DEL PERIODO\nAnálisis de IA no disponible.\n# 02 — ESTADO DEL FLUJO DE TRABAJO Y CUELLOS DE BOTELLA\nAnálisis de IA no disponible.\n# 03 — ANÁLISIS DE PREDICTIBILIDAD Y RIESGOS\nAnálisis de IA no disponible.\n# 04 — CONCLUSIONES ESTRATÉGICAS Y PLAN DE ACCIÓN\nAnálisis de IA no disponible.\n"""
    else:
        return """# 01 — RESUMEN DEL SPRINT\nAnálisis de IA no disponible.\n\n# 02 — DESEMPEÑO Y VELOCIDAD\nAnálisis de IA no disponible.\n\n# 03 — FLUJO Y ESTABILIDAD\nAnálisis de IA no disponible.\n\n# 04 — PLAN DE MEJORA CONTINUA\nAnálisis de IA no disponible.\n"""

def _build_sprint_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    return f"""
Actúa como un Scrum Master experto analizando el desempeño del sprint actual.
Tu objetivo es realizar un reporte analítico basándote en estos datos empíricos:
Velocidad: {v} SP
Throughput: {t} tickets
Cycle Time: {ct} días
Bloqueos: {bd} días
Bugs: {bugs}
Salud: {health}/100

No uses formato de 'plantilla de IA'. Escribe párrafos fluidos y reflexivos.

ESTRUCTURA ESTRICTA DE CADA SECCIÓN (OBLIGATORIO):
El sistema separa el reporte usando etiquetas '# 0X — TITULO'.
1. TITULO EN FORMATO H1 (# 0X — TITULO).
2. ANALISIS FLUIDO.

LAS 4 SECCIONES A DESARROLLAR (Debes incluir EXACTAMENTE estas 4 en este orden):

# 01 — RESUMEN DEL SPRINT
  - Escribe un párrafo inicial resumiendo la evaluación general del periodo y su salud.

# 02 — DESEMPEÑO Y VELOCIDAD
  - Redacta un análisis reflexivo sobre la velocidad y throughput alcanzados.

# 03 — FLUJO Y ESTABILIDAD
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_BURNUP]
  - Escribe un análisis profundo del flujo de trabajo, el cycle time y cómo los bloqueos impactaron la entrega.
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_VELOCIDAD]

# 04 — PLAN DE MEJORA CONTINUA
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_FLUJO]
  - Basado en los datos técnicos, propón 2 o 3 acciones de mejora estructurales en formato de párrafo fluido.
"""
