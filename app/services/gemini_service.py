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
