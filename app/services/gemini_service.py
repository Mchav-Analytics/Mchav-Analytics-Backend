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

    primary_model = GEMINI_MODEL_NAME or "gemini-2.5-flash"
    candidate_models = list(dict.fromkeys([primary_model, "gemini-2.5-flash", "gemini-1.5-flash", "gemini-flash-lite-latest"]))

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

    with httpx.Client(timeout=30.0) as client:
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
                    print(f"Modelo Gemini '{model}' no disponible (404), intentando siguiente modelo...")
                    continue
                else:
                    print(f"Aviso Gemini API ({model} HTTP {response.status_code}): {response.text[:150]}")
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
Actúa como un Asistente Analítico Experto, consultor senior de agilidad de MCHAV Analytics. No te presentes, no digas tu nombre ni uses saludos iniciales.
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
    kanban_note = ""
    if v == 0 and t > 0:
        kanban_note = f" (Nota: El equipo opera en modalidad Kanban basada en Throughput con {t} incidencias cerradas. No alarmes por '0 Story Points', enfoca el análisis en los tickets terminados)."

    return f"""
Actúa como un Senior Agile Data Scientist evaluando la evolución multitemporal del proyecto.
Tu informe DEBE responder rigurosamente a la pregunta central: "¿Cómo ha evolucionado el proyecto durante el periodo?" comparando, cuando sea posible, con periodos anteriores.

DATOS ANALÍTICOS REALES Y UNIFICADOS DEL PROYECTO:
- Velocidad: {v} Story Points completados.{kanban_note}
- Rendimiento (Throughput): {t} tickets/incidencias completadas.
- Tiempo de ciclo promedio: {ct} días hábiles (excluyendo fines de semana y festivos).
- Días bloqueados acumulados: {bd} días.
- Bugs / Defectos escapados: {bugs}.
- Alcance total evaluado: {scope} Story Points.
- Salud global del proyecto (Health Score): {health}/100 pts.
- Percentiles de Cycle Time: P50 (Mediana)={p50} días, P85 (SLA objetivo)={p85} días, P95 (Outliers)={p95} días.
- Porcentaje de completitud: {pct}%.

REGLAS ESTRICTAS DE REDACCIÓN Y TONO TÉCNICO (CUMPLIMIENTO OBLIGATORIO):
1. PROHIBIDO usar adjetivos subjetivos (ej. 'con creces', 'considerablemente', 'significativamente'). Todo debe expresarse en variaciones porcentuales o valores absolutos.
2. PROHIBIDO invocar 'intervención gerencial', 'intervención ejecutiva' o tonos punitivos. Mantén un enfoque analítico, constructivo y centrado en la mejora del equipo.
3. EL TEXTO DEBE INTERPRETAR DIRECTAMENTE LAS GRÁFICAS. Ej: "En la gráfica de velocidad se observa...", "La línea de alcance del Burnup muestra...".
4. ESTRUCTURA LA EVALUACIÓN EN 3 NIVELES: a) Dato observado → b) Relación o tendencia → c) Conclusión analítica.
5. Reconoce matices: Por ejemplo, los tiempos atípicos (P95) suelen deberse a la complejidad (Story Points) o dependencias externas.

ESTRUCTURA DE SECCIONES (Utiliza exactamente estas etiquetas [PROYECTO_X]):

[PROYECTO_1] FICHA DEL PROYECTO Y ESTADO GENERAL
  - Resume la muestra evaluada: periodo, Sprints incluidos, {t} tickets analizados, {scope} SP de alcance total y la salud ({health}/100).

[PROYECTO_2] EVOLUCIÓN DE LA ENTREGA
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_VELOCIDAD]
  - Analiza la gráfica de Histórico de Velocidad. Explica los {v} SP y {t} tickets completados frente a lo planificado ({planned} SP). Compara periodos (sprints) e identifica la tendencia de entrega (alza, baja o estable).

[PROYECTO_3] EVOLUCIÓN DEL FLUJO Y WIP
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_FLUJO]
  - Analiza el Diagrama CFD: cómo evolucionó el WIP por semana/sprint, en qué estados se acumula el trabajo y cómo impactaron los bloqueos.

[PROYECTO_4] EVOLUCIÓN DE LOS TIEMPOS Y PREDICTIBILIDAD
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_PREDICTIBILIDAD]
  - Analiza el Scatter Plot usando los percentiles (P50: {p50}d, P85: {p85}d, P95: {p95}d). Explica los casos atípicos considerando la complejidad y los días no laborales.

[PROYECTO_5] ALCANCE, CAMBIOS Y TRABAJO PENDIENTE
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_BURNUP]
  - Interpreta el Burnup Chart evaluando el alcance comprometido frente al completado. Menciona si hubo trabajo añadido y cuánto trabajo pendiente real existe.

[PROYECTO_6] RIESGOS Y OPORTUNIDADES
  - Identifica acumulación recurrente, variabilidad de tiempos ({ct} días en promedio) o dependencias/bloqueos ({bd} días).

[PROYECTO_7] CONCLUSIONES ESTRATÉGICAS DE IA
  - Responde de manera contundente: ¿El proyecto está mejorando, empeorando o manteniéndose? Analiza patrones entre sprints y provee 2 recomendaciones concretas.
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
def _build_pdf_monthly_prompt(metrics):
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

    return f"""
Actúa como un Senior Agile Data Scientist y Director Analítico. Eres el encargado de redactar el texto de un reporte ejecutivo mensual en PDF para C-levels y líderes.
Tu tono debe ser profesional, analítico, directo al grano y sin rodeos. Nada de introducciones ni saludos.

Datos del mes:
- Velocidad: {v} Story Points completados.
- Rendimiento (Throughput): {t} tickets completados.
- Tiempo de ciclo promedio: {ct} días hábiles.
- Días bloqueados acumulados: {bd} días.
- Bugs reportados/resueltos: {bugs}.
- Alcance total planificado: {scope} Story Points.
- Salud global del sprint/mes: {health}/100.
- Predictibilidad (Percentiles): P50={p50}d, P85={p85}d, P95={p95}d.
- Completitud de entrega: {pct}%.

REGLAS OBLIGATORIAS:
1. Tono ejecutivo, estratégico y extremadamente directo al grano.
2. No uses adornos, saludos, ni palabras de relleno. Ve directo al dato y su implicación.
3. ESTRUCTURA LA EVALUACIÓN EN 3 NIVELES para cada sección: a) Dato observado → b) Tendencia → c) Impacto.
4. Genera el contenido ESTRICTAMENTE utilizando las siguientes etiquetas y escribe MÁXIMO 2 a 3 LÍNEAS por cada sección. No te extiendas.

[PROYECTO_RESUMEN]
(Resumen ejecutivo general del mes. Cita {t} tickets, {v} SP y la salud {health}/100 para dar un veredicto claro).

[PROYECTO_ENTREGA]
(Analiza la evolución de la entrega -Burnup-. Menciona la completitud del {pct}% respecto al alcance de {scope} SP).

[PROYECTO_FLUJO]
(Analiza el flujo de trabajo -CFD-. Evalúa la fricción por los {bd} días bloqueados y los estancamientos).

[PROYECTO_TIEMPOS]
(Analiza la predictibilidad y el Cycle Time medio de {ct}d. Menciona que el 85% se resuelve en {p85} días o menos).

[PROYECTO_CAPACIDAD]
(Analiza la capacidad del equipo basándote en la velocidad y estabilidad del throughput mensual).

[PROYECTO_CALIDAD]
(Analiza la calidad técnica basándote en los {bugs} bugs y su impacto en el trabajo).

[PROYECTO_HALLAZGOS]
(Identifica 2 hallazgos principales del mes con evidencia cuantitativa).

[PROYECTO_EVOLUCION]
(Interpreta la evolución frente a las expectativas operativas del periodo).

[PROYECTO_MEJORA]
(Propón 2 recomendaciones directas y tácticas para el equipo y el Líder Técnico).

[PROYECTO_CONCLUSION]
(Un párrafo corto de conclusión estratégica sobre la viabilidad y ritmo actual del proyecto).
"""

def _build_lider_pdf_monthly_prompt(metrics):
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

    return f"""
Actúa como un Asistente Analítico Experto y Facilitador Ágil. Eres el encargado de redactar el texto de un reporte mensual en PDF para el Líder Técnico y el equipo de desarrollo.
Tu tono debe ser táctico, directo al grano y enfocado en la mejora continua y resolución de impedimentos operativos. Nada de introducciones ni saludos.

Datos del mes:
- Velocidad: {v} Story Points completados.
- Rendimiento (Throughput): {t} tickets completados.
- Tiempo de ciclo promedio: {ct} días hábiles.
- Días bloqueados acumulados: {bd} días.
- Bugs reportados/resueltos: {bugs}.
- Alcance total planificado: {scope} Story Points.
- Salud global del sprint/mes: {health}/100.
- Predictibilidad (Percentiles): P50={p50}d, P85={p85}d, P95={p95}d.
- Completitud de entrega: {pct}%.

REGLAS OBLIGATORIAS:
1. Tono táctico, enfocado en el equipo, cuellos de botella y calidad técnica.
2. No uses adornos, saludos, ni palabras de relleno. Ve directo al dato y su implicación técnica.
3. ESTRUCTURA LA EVALUACIÓN EN 3 NIVELES para cada sección: a) Dato observado → b) Causa raíz u obstáculo → c) Acción recomendada.
4. Genera el contenido ESTRICTAMENTE utilizando las siguientes etiquetas y escribe MÁXIMO 2 a 3 LÍNEAS por cada sección. No te extiendas.

[PROYECTO_RESUMEN]
(Resumen técnico general del mes. Cita {t} tickets, {v} SP y la salud {health}/100 para evaluar el ritmo del equipo).

[PROYECTO_ENTREGA]
(Analiza la completitud del {pct}% respecto al alcance de {scope} SP. ¿Hubo deuda o spillover?).

[PROYECTO_FLUJO]
(Analiza el CFD. Evalúa dónde están los cuellos de botella y el impacto de los {bd} días bloqueados).

[PROYECTO_TIEMPOS]
(Analiza el Cycle Time de {ct}d y el P85 de {p85}d. ¿El equipo está perdiendo tiempo en bucles de revisión o QA?).

[PROYECTO_CAPACIDAD]
(Analiza si el equipo está sobrecargado o si la velocidad está fragmentada en micro-tareas).

[PROYECTO_CALIDAD]
(Analiza la incidencia de los {bugs} bugs en la arquitectura y si falta refinamiento).

[PROYECTO_HALLAZGOS]
(Identifica 2 fricciones operativas principales del mes con evidencia cuantitativa).

[PROYECTO_EVOLUCION]
(Interpreta si el equipo ha mejorado sus prácticas técnicas respecto a periodos anteriores).

[PROYECTO_MEJORA]
(Propón 2 prácticas ágiles o de ingeniería directas que el Líder Técnico debe implementar de inmediato).

[PROYECTO_CONCLUSION]
(Un párrafo corto de conclusión técnica sobre el estado de salud operativa del equipo).
"""

def generate_report_insights(metrics: dict, fallback: dict, report_type: str = "sprint", is_leader: bool = False) -> str:
    cache_key = f"rep_insights_{report_type}_{is_leader}_{metrics.get('targetName') or metrics.get('sprintName') or metrics.get('projectName')}_{metrics.get('velocity',0)}_{metrics.get('throughput',0)}"
    cached = gemini_cache.get(cache_key)
    if cached:
        return cached

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

        if report_type == "general" or report_type == "cierre_general":
            prompt = _build_lider_general_prompt(metrics)
        elif report_type == "desarrollador" or report_type == "cierre_desarrollador":
            prompt = _build_lider_desarrollador_prompt(metrics, v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct)
        elif report_type == "monthly_pdf":
            prompt = _build_lider_pdf_monthly_prompt(metrics)
        elif report_type == "proyecto":
            prompt = _build_lider_proyecto_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct)
        elif report_type == "cierre_proyecto":
            prompt = _build_cierre_proyecto_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct)
        elif report_type == "sprint_comparativo":
            s_base = metrics.get("sprintNameBase", "Sprint Base")
            s_comp = metrics.get("sprintNameCompare", "Sprint A Comparar")
            prompt = f"""
Actúa como un Asistente Analítico Experto del Líder Técnico. No te presentes, no digas tu nombre ni uses saludos iniciales.
Analiza y compara tácticamente el desempeño de {s_base} frente a {s_comp}, enfocándote en la coordinación del equipo y resolución de impedimentos.

DATOS {s_base}:
Velocidad: {metrics.get("velocity", 0)} SP. Throughput: {metrics.get("throughput", 0)} tickets. Cycle Time: {metrics.get("cycleTime", 0)} días. Bloqueos: {metrics.get("blockedDays", 0)} días. Salud: {metrics.get("sprintHealth", 0)}/100.

DATOS {s_comp}:
Velocidad: {metrics.get("velocityCompare", 0)} SP. Throughput: {metrics.get("throughputCompare", 0)} tickets. Cycle Time: {metrics.get("cycleTimeCompare", 0)} días. Bloqueos: {metrics.get("blockedDaysCompare", metrics.get("blockedDays", 0))} días. Salud: {metrics.get("sprintHealthCompare", 0)}/100.

Estructura tu respuesta estrictamente en estas 4 secciones:

# 01 — ANÁLISIS DE RENDIMIENTO CRUZADO
  - Analiza las diferencias clave en velocidad y throughput entre ambos ciclos desde la perspectiva de liderazgo.

# 02 — COMPARATIVA DE VELOCIDAD
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_COMPARATIVA_VELOCIDAD]
  - Interpreta la gráfica evaluando el esfuerzo y compromiso del equipo.

# 03 — CUELLOS DE BOTELLA Y FLUJO DE TRABAJO
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_COMPARATIVA_FLUJO]
  - Compara los bloqueos y la acumulación de WIP.

# 04 — ESTRATEGIA Y ACCIONES DEL LÍDER
  - Propón 3 acciones claras que el Líder Técnico debe tomar basándose en esta comparación.
"""
        else:
            prompt = _build_lider_sprint_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct)
    elif report_type == "monthly_pdf":
        prompt = _build_pdf_monthly_prompt(metrics)
    elif report_type == "general" or report_type == "cierre_general":
        prompt = _build_general_prompt(metrics)
    elif report_type == "desarrollador" or report_type == "cierre_desarrollador":
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
    elif report_type == "cierre_proyecto":
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
        prompt = _build_cierre_proyecto_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct)
    elif report_type == "sprint_comparativo":
        s_base = metrics.get("sprintNameBase", "Sprint Base")
        s_comp = metrics.get("sprintNameCompare", "Sprint A Comparar")
        
        # Sprint 1 data
        periodo1 = s_base
        comp1 = metrics.get("planned1", 0)
        pts1 = metrics.get("velocity", 0)
        v1 = metrics.get("velocity", 0)
        t1 = metrics.get("throughput", 0)
        ct1 = metrics.get("cycleTime", 0)
        pred1 = metrics.get("predictability1", 0)
        tc1 = metrics.get("ticketsCompleted1", 0)
        tp1 = metrics.get("ticketsPending1", 0)
        h1 = metrics.get("sprintHealth", 0)
        
        # Sprint 2 data
        periodo2 = s_comp
        comp2 = metrics.get("planned2", 0)
        pts2 = metrics.get("velocityCompare", 0)
        v2 = metrics.get("velocityCompare", 0)
        t2 = metrics.get("throughputCompare", 0)
        ct2 = metrics.get("cycleTimeCompare", 0)
        pred2 = metrics.get("predictability2", 0)
        tc2 = metrics.get("ticketsCompleted2", 0)
        tp2 = metrics.get("ticketsPending2", 0)
        h2 = metrics.get("sprintHealthCompare", 0)
        
        prompt = f"""
Actúa como un Agile Coach especializado en análisis de métricas ágiles.

Analiza y compara el desempeño de {s_base} frente a {s_comp}, utilizando exclusivamente los datos proporcionados.

DATOS DEL SPRINT BASE:
- Periodo: {periodo1}
- Puntos comprometidos: {comp1}
- Puntos completados: {pts1}
- Velocity: {v1}
- Throughput: {t1}
- Cycle Time: {ct1}
- Predictibilidad: {pred1}%
- Tickets completados: {tc1}
- Tickets pendientes: {tp1}
- Salud: {h1}/100

DATOS DEL SPRINT A COMPARAR:
- Periodo: {periodo2}
- Puntos comprometidos: {comp2}
- Puntos completados: {pts2}
- Velocity: {v2}
- Throughput: {t2}
- Cycle Time: {ct2}
- Predictibilidad: {pred2}%
- Tickets completados: {tc2}
- Tickets pendientes: {tp2}
- Salud: {h2}/100

REGLAS DE ANÁLISIS:
- Compara las métricas entre ambos sprints y menciona únicamente diferencias respaldadas por los datos.
- Indica qué métricas mejoraron, cuáles disminuyeron y cuáles permanecieron estables.
- Explica qué significan esas variaciones para el flujo de trabajo y la capacidad de entrega.
- Relaciona el análisis con las gráficas y métricas mostradas en el reporte; no describas una gráfica sin explicar qué significa el comportamiento observado.
- Cuando sea posible, expresa las variaciones en porcentajes o diferencias concretas.
- No atribuyas causas que no estén respaldadas por los datos.
- No inventes información, eventos, bloqueos, causas o comportamientos de los desarrolladores.
- No utilices expresiones subjetivas como "excelente", "malo", "con creces" o similares.
- No declares un "ganador" general. Presenta objetivamente las principales mejoras, retrocesos y aspectos que requieren atención.

FORMATO:
Redacta entre 2 y 3 párrafos continuos, profesionales y fáciles de leer.
No utilices títulos, listas, viñetas ni enumeraciones.
Evita repetir los valores de todas las métricas; selecciona únicamente los datos relevantes para explicar los cambios.
El texto debe sentirse como una interpretación del reporte y no como una repetición de sus cifras.
"""
    elif report_type == "sprint_historico":
        v = metrics.get("velocity", 0)
        h = metrics.get("sprintHealth", 0)
        s_base = metrics.get("sprintNameBase", "Sprint")
        prompt = f"""
Actúa como un Agile Coach analizando el desempeño histórico de {s_base}.
Puntos completados = {v}, Salud = {h}/100.
Redacta directamente 2 párrafos limpios resumiendo el desempeño de este sprint histórico. Sin títulos, sin secciones, sin enumeraciones, solo texto continuo y profesional.
"""
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

    # Reglas globales de fidelidad y tono: aplican a TODOS los reportes (Admin y Líder)
    prompt = f"{prompt}\n{_build_fidelity_rules(metrics)}"
    reply = _call_gemini_rest_api(prompt, temperature=0.4, max_tokens=2500)
    if reply:
        sanitized = _sanitize_ai_reply(reply)
        gemini_cache.set(cache_key, sanitized)
        return sanitized

    fb = _get_fallback_insights(report_type)
    gemini_cache.set(cache_key, fb)
    return fb

def _build_fidelity_rules(metrics: dict) -> str:
    """Reglas anti-invención y anti-alarmismo que se anexan al final de cada prompt de reporte."""
    try:
        health = float(metrics.get("sprintHealth", 0) or 0)
    except (TypeError, ValueError):
        health = 0
    urgency_rule = (
        f"- La salud es {health:.0f}/100 (estable): PROHIBIDO expresar urgencia (\"inmediato\", \"urgente\", \"crítico\", \"exige\"). Usa \"se recomienda\"."
        if health >= 70 else
        "- Aunque la salud sea baja, describe la situación con datos y tono constructivo, sin dramatizar."
    )
    return f"""
REGLAS FINALES OBLIGATORIAS (prevalecen sobre cualquier instrucción anterior):
- Usa ÚNICAMENTE las métricas entregadas arriba. No inventes cifras, causas ni contexto.
- PROHIBIDO atribuir causas que no estén en los datos (p. ej. falta de pruebas unitarias, pipelines, arquitectura, integraciones, code reviews, criterios DoD). Si sugieres una causa, preséntala como hipótesis a validar ("podría estar asociado a...").
- PROHIBIDO afirmar tendencias históricas ("sostenida", "en los últimos ciclos", "creció", "cayó") si no se entregaron datos de periodos anteriores.
- PROHIBIDO afirmar impacto en producción o en clientes si no hay datos que lo respalden.
{urgency_rule}
- Escribe siempre los porcentajes con el símbolo % (ej. 86%).
"""


def _strip_accents(s: str) -> str:
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _accent_insensitive_regex(phrase: str) -> str:
    """Convierte una frase en un patrón regex que acepta la versión con o sin tildes (para BUSCAR).
    El texto original del reporte no se modifica: solo se reemplaza la frase encontrada."""
    import re
    variants = {"a": "[aáà]", "e": "[eéè]", "i": "[iíì]", "o": "[oóò]", "u": "[uúüù]"}
    base = _strip_accents(phrase.lower())
    return "".join(variants.get(ch, re.escape(ch)) for ch in base)


def _match_case(original: str, replacement: str) -> str:
    """Si la frase original empezaba en mayúscula (inicio de oración), el reemplazo también."""
    if original[:1].isupper() and replacement:
        return replacement[0].upper() + replacement[1:]
    return replacement


def _sanitize_ai_reply(text: str) -> str:
    """Elimina o suaviza frases alarmistas o imprecisas generadas por la IA.
    La búsqueda ignora tildes y mayúsculas; el reemplazo conserva la ortografía correcta."""
    import re
    if not text:
        return ""
    # Orden importa: frases largas primero
    replacements = [
        ("ceros absolutos en velocidad", "flujo de trabajo enfocado en Throughput"),
        ("ceros absolutos", "ausencia de estimaciones en puntos"),
        ("parálisis total", "operación en flujo continuo"),
        ("desconexión crítica", "oportunidad de mejora en la trazabilidad de estimaciones"),
        ("teletransportación de código", "registro dinámico de incidencias"),
        ("intervención gerencial", "apoyo técnico al equipo"),
        ("intervención ejecutiva", "seguimiento facilitador"),
        ("intervención inmediata", "acciones de mejora"),
        ("exige correcciones inmediatas", "sugiere ajustes"),
        ("requiere correcciones inmediatas", "sugiere ajustes"),
        ("correcciones inmediatas", "ajustes recomendados"),
        ("acciones inmediatas", "acciones recomendadas"),
        ("medidas inmediatas", "medidas recomendadas"),
        ("atención inmediata", "seguimiento"),
        ("de inmediato", "en el próximo ciclo"),
        ("de manera urgente", "de forma prioritaria"),
        ("insostenible", "con oportunidad de optimización"),
        ("con creces", "cumpliendo los criterios definidos"),
    ]
    res = str(text)
    for old, new in replacements:
        pattern = r"\b" + _accent_insensitive_regex(old) + r"\b"
        res = re.sub(pattern, lambda m, n=new: _match_case(m.group(0), n), res, flags=re.IGNORECASE)
    # Corrección de marca (respeta mayúsculas exactas)
    res = res.replace("ANACITYCS", "ANALYTICS")
    return res

def _build_lider_sprint_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    spillover = max(0, planned - v)
    return f"""
Actúa como un Asistente Analítico Experto del Líder Técnico y Facilitador Ágil. No te presentes, no digas tu nombre ni uses saludos iniciales.
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

# 03 — CUELLOS DE BOTELLA Y FLUJO DE TRABAJO
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_BURNUP]
  - Analiza las causas de los {bd} días bloqueados y la evolución temporal.
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_VELOCIDAD]

# 04 — LOCALIZACIÓN DEL PROBLEMA Y PLAN TÁCTICO
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_FLUJO]
  - Analiza la concentración de tareas en revisión en el CFD, cuantificando las horas de retraso estimadas y el impacto de la multitarea.
  - Proporciona 3 acciones prácticas para que el Líder Técnico y el equipo rebalanceen el WIP y remuevan bloqueos en el próximo sprint.
"""

def _build_lider_proyecto_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    spillover = max(0, planned - v)
    return f"""
Actúa como un Asistente Analítico Experto del Líder Técnico y Facilitador Ágil. No te presentes, no digas tu nombre ni uses saludos iniciales.
Analiza el proyecto con los datos:
Velocidad entregada: {v} SP de {planned} SP planificados ({pct}% de cumplimiento). Throughput: {t} tickets resueltos. Tareas en deuda: {spillover} SP. Cycle Time medio: {ct} días hábiles (descontando fines de semana); P85: {p85}d; P95: {p95}d. Días bloqueados: {bd}. Bugs: {bugs}. Salud: {health}/100.

REGLAS OBLIGATORIAS DE TONO Y ESTILO:
1. Utiliza un tono constructivo, de soporte y enfocado en la mejora continua del equipo.
2. ESTRUCTURA LA EVALUACIÓN EN 3 NIVELES: a) Dato observado → b) Relación o tendencia → c) Conclusión o acción táctica.
3. BREVEDAD ESTRICTA: cada nivel (a, b, c) es UNA sola línea corta. Máximo 3 líneas por sección. Sin relleno.

ESTRUCTURA DE SECCIONES (Utiliza exactamente estas etiquetas [PROYECTO_X]):

[PROYECTO_RESUMEN]
{t} tickets completados, {pct}% del alcance y {spillover} SP pendientes: qué significan juntos.

[PROYECTO_ENTREGA]
Velocidad y throughput: qué implica este volumen para la planificación del equipo.

[PROYECTO_FLUJO]
Fricción generada por los {bd} días bloqueados y acción táctica para reducirla.

[PROYECTO_TIEMPOS]
Cycle Time ({ct}d, P85 {p85}d): estabilidad del flujo y acción sobre la cola larga.

[PROYECTO_CAPACIDAD]
Velocidad ({v} SP) frente a lo planificado ({planned} SP) y ajuste de compromiso sugerido.

[PROYECTO_CALIDAD]
Los {bugs} bugs en relación con los {t} tickets entregados.

[PROYECTO_HALLAZGOS]
3 hallazgos con evidencia numérica de los datos anteriores (una línea cada uno).

[PROYECTO_EVOLUCION]
Si no hay datos de periodos anteriores, escribe exactamente: "Sin datos del periodo anterior para comparar."

[PROYECTO_MEJORA]
3 recomendaciones (Hallazgo → Acción → Objetivo medible), una línea cada una.

[PROYECTO_CONCLUSION]
Una sola línea: cómo terminó el periodo.
"""

def _build_cierre_proyecto_prompt(v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    spillover = max(0, planned - v)
    return f"""
Actúa como un Director Ejecutivo y Asistente Analítico. No te presentes, no digas tu nombre ni uses saludos iniciales.
Genera el informe de CIERRE MENSUAL DEL PROYECTO con los datos:
Velocidad entregada: {v} SP. Throughput: {t} tickets resueltos. Tareas en deuda: {spillover} SP. Cycle Time medio: {ct} días hábiles. Días bloqueados: {bd}. Bugs: {bugs}.

REGLAS OBLIGATORIAS:
1. Tono ejecutivo, estratégico y orientado a resultados de negocio del mes.
2. ESTRUCTURA LA EVALUACIÓN EN 3 NIVELES: a) Dato observado → b) Relación o tendencia → c) Impacto mensual.

ESTRUCTURA DE SECCIONES (Utiliza exactamente estas etiquetas con los nuevos títulos para el Cierre Mensual):

[PROYECTO_1] RESUMEN EJECUTIVO DEL MES
Analiza brevemente los {t} tickets completados y {spillover} SP pendientes.

[PROYECTO_2] IMPACTO Y ENTREGABLES (VELOCIDAD)
Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_VELOCIDAD]
Analiza la evolución de la entrega mensual basándote en la velocidad y el throughput.

[PROYECTO_3] CUELLOS DE BOTELLA Y FLUJO MENSUAL
Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_FLUJO]
Evalúa los {bd} días bloqueados y los estancamientos del mes.

[PROYECTO_4] PREDICTIBILIDAD Y TIEMPOS DE RESPUESTA
Inyecta OBLIGATORIAMENTE la etiqueta: [GRAFICA_PREDICTIBILIDAD]
Analiza el Cycle Time (P50: {p50}d, P85: {p85}d, P95: {p95}d).

[PROYECTO_5] ALCANCE, DEUDA TÉCNICA Y DEFECTOS
Analiza los {bugs} bugs y el scope creep del mes.

[PROYECTO_6] SALUD GENERAL DEL PROYECTO
Analiza la salud global ({health}/100) del proyecto al cierre del mes.

[PROYECTO_7] PLAN DE ACCIÓN PARA EL PRÓXIMO MES
Propón 3 recomendaciones específicas o directrices ejecutivas para el mes que entra.
"""

def _build_lider_desarrollador_prompt(metrics, v, t, ct, bd, bugs, scope, health, p50, p85, p95, planned, pct):
    return f"""
Actúa como un Asistente Analítico Experto del Líder Técnico. No te presentes, no digas tu nombre ni uses saludos iniciales.
Analiza la actividad del desarrollador con los datos:
Story Points completados: {v} SP. Tareas cerradas: {t}. Cycle Time personal: {ct} días hábiles. Días de bloqueo: {bd}. Bugs reabiertos: {bugs}.

REGLAS DE TONO: Tono positivo, de coaching técnico y crecimiento profesional. Cero lenguaje punitivo o jerárquico.

Estructura la evaluación narrativa en 4 secciones EXACTAMENTE, usando los títulos obligatorios y etiquetas:

# 01 — PERFIL Y CARGA DE TRABAJO ACTUAL
  - Resumen de entregas cerradas ({t} tareas, {v} SP) y nivel de enfoque en el periodo.
  - Inyecta OBLIGATORIAMENTE la etiqueta: [TABLA_EVOLUCION]

# 02 — RITMO DE ENTREGA Y EVOLUCIÓN
  - Analiza la estabilidad de velocidad individual y el impacto de los {v} SP entregados.
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRÁFICA_VELOCIDAD]

# 03 — IDENTIFICACIÓN DE IMPEDIMENTOS Y MULTITAREA
  - Evalúa la presencia de sobrecarga por WIP simultáneo, cuellos de botella en QA o días bloqueados ({bd} días).
  - Inyecta OBLIGATORIAMENTE la etiqueta: [GRÁFICA_FLUJO]

# 04 — PLAN DE ACOMPAÑAMIENTO Y MENTORÍA TÉCNICA
  - Recomendaciones para el Líder Técnico sobre cómo apoyar al desarrollador, despejar bloqueos y balancear sus asignaciones.
"""

def _build_lider_general_prompt(metrics):
    return f"""
Actúa como un Asistente Analítico Experto del Líder Técnico. No te presentes, no digas tu nombre ni uses saludos iniciales.
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
        return """# 01 — VISIÓN GENERAL DEL PORTAFOLIO
El presente informe consolida el rendimiento general del portafolio multi-proyecto de MCHAV Analytics.

# 02 — RESUMEN EJECUTIVO Y TABLA DE PORTAFOLIO
[TABLA_PORTAFOLIO]

# 03 — DESEMPEÑO COMPARATIVO DE VELOCIDAD
[GRAFICA_PORTAFOLIO_VELOCIDAD]

# 04 — ESTRUCTURA DE FLUJO Y EFICIENCIA
Se analizan los indicadores agregados de entrega a nivel portafolio.

# 05 — CONCLUSIONES Y RECOMENDACIONES TÁCTICAS
El equipo mantiene una operación estable a lo largo de las distintas iniciativas evaluadas.
"""
    elif report_type == "monthly_pdf":
        return """[PROYECTO_RESUMEN]
El equipo mantuvo un progreso constante, con una entrega sostenida y gestión efectiva de las incidencias críticas.

[PROYECTO_ENTREGA]
El alcance general se abordó conforme a las previsiones, con ligeras fluctuaciones propias de la naturaleza del mes.

[PROYECTO_FLUJO]
El flujo de tareas evidencia periodos cortos de acumulación en validación (QA), que fueron resueltos progresivamente.

[PROYECTO_TIEMPOS]
Los percentiles de entrega se mantienen estables, logrando resoluciones predecibles dentro de las franjas habituales.

[PROYECTO_CAPACIDAD]
La capacidad del equipo se encuentra nivelada, logrando entregar una cantidad de puntos congruente con su histórico reciente.

[PROYECTO_CALIDAD]
Los defectos detectados se resolvieron sin poner en alto riesgo el desempeño estructural del periodo.

[PROYECTO_HALLAZGOS]
El equipo demuestra adaptabilidad ante bloqueos y sostiene una dinámica de entrega predecible.

[PROYECTO_EVOLUCION]
El periodo refleja estabilidad general al compararse con el mes anterior, consolidando los flujos de trabajo.

[PROYECTO_MEJORA]
Se sugiere continuar refinando el control de tareas en progreso y fortalecer el tiempo de revisión técnica.

[PROYECTO_CONCLUSION]
El mes concluye en un estado general saludable y con directrices claras para el próximo ciclo.
"""
    elif report_type == "desarrollador":
        return """# 01 — PERFIL Y DESEMPEÑO INDIVIDUAL
Diagnóstico operativo de desempeño individual.

[TABLA_EVOLUCION]

# 02 — ACTIVIDAD Y HISTÓRICO DE ENTREGAS
[GRAFICA_VELOCIDAD]

# 03 — FLUJO DE TRABAJO Y WIP
[GRAFICA_FLUJO]

# 04 — PLAN DE ACOMPAÑAMIENTO Y RECOMENDACIONES
Se recomienda mantener la gestión controlada del WIP y priorizar el cierre de tareas en progreso.
"""
    elif report_type == "proyecto":
        return """[PROYECTO_1] FICHA DEL PROYECTO Y ESTADO GENERAL
El presente informe evalúa la evolución operativa, evaluando la tendencia de entrega y la salud técnica del proyecto.

[PROYECTO_2] EVOLUCIÓN DE LA ENTREGA
[GRAFICA_VELOCIDAD]
La gráfica de histórico de velocidad evidencia la relación entre el trabajo comprometido y el entregado durante los sprints analizados.

[PROYECTO_3] EVOLUCIÓN DEL FLUJO Y WIP
[GRAFICA_FLUJO]
El diagrama de flujo acumulado muestra la distribución de las tareas y permite visualizar dónde se concentra el trabajo en progreso.

[PROYECTO_4] EVOLUCIÓN DE LOS TIEMPOS Y PREDICTIBILIDAD
[GRAFICA_PREDICTIBILIDAD]
La distribución de tiempos de ciclo expone la predictibilidad del equipo, destacando que la mayor parte del trabajo se resuelve dentro de los márgenes esperados, aunque existen casos atípicos asociados a complejidad o bloqueos.

[PROYECTO_5] ALCANCE, CAMBIOS Y TRABAJO PENDIENTE
[GRAFICA_BURNUP]
El seguimiento del alcance evidencia cómo evoluciona el trabajo pendiente respecto a los compromisos iniciales.

[PROYECTO_6] RIESGOS Y OPORTUNIDADES
Se recomienda monitorear activamente los picos de trabajo en progreso y gestionar las dependencias para evitar cuellos de botella prolongados.

[PROYECTO_7] CONCLUSIONES ESTRATÉGICAS DE IA
A lo largo de los periodos evaluados, el proyecto mantiene una capacidad de entrega funcional. Se sugiere estabilizar la planificación para reducir la variabilidad entre sprints.
"""
    else:
        return """# 01 — INTRODUCCIÓN Y CONTEXTO DEL SPRINT
El reporte analiza el desempeño del equipo en el sprint actual.

# 02 — RESUMEN EJECUTIVO Y MÉTRICAS CLAVE
%%HIGHLIGHT%%
El equipo registró un cumplimiento sostenido de su capacidad planificada, manteniendo la estabilidad operativa.
%%

# 03 — GESTIÓN DE ALCANCE Y VELOCIDAD
[GRAFICA_BURNUP]
[GRAFICA_VELOCIDAD]

# 04 — EVOLUCIÓN DEL FLUJO Y CUELLOS DE BOTELLA
[GRAFICA_FLUJO]

# 05 — TIEMPOS DE CICLO Y PREDICTIBILIDAD
[GRAFICA_PREDICTIBILIDAD]
"""

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
