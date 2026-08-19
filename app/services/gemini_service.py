# app/services/gemini_service.py
# Servicio de Inteligencia Artificial Generativa impulsado por Google Gemini API (gemini-2.5-flash)
# Proporciona diagnósticos analíticos en tiempo real para:
# 1. AI Dev Coach (Mascota Búho en la vista de Desarrollador)
# 2. Dashboard del Líder Técnico (Salud del sprint y alertas de cuellos de botella)
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
    Genera un consejo inteligente y empático del AI Dev Coach (Mascota Búho) impulsado por Gemini.
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
Eres 'AI Dev Coach', un búho sabio, entusiasta y experto en metodologías ágiles y analítica de software.
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
    Genera diagnósticos analíticos ejecutivos para el Dashboard del Líder Técnico impulsados por Gemini.
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
Eres el consultor senior de agilidad e IA de MCHAV Analytics. Genera un diagnóstico ejecutivo para el Líder Técnico.

Métricas del Proyecto ({proj_id}):
- Salud Global del Sprint: {health_score}/100 pts.
- Cumplimiento del Compromiso (Commitment Reliability): {commitment}%.
- Alcance agregado (Scope Creep): +{scope_creep} Story Points.
- Eficiencia de Flujo: {flow_eff}%.
- Alertas activas de cuellos de botella: {alert_count} alertas.

Devuelve un JSON estrictamente válido con la siguiente estructura (sin comillas de código markdown extra):
{{
  "diagnostico_ejecutivo": "2 frases con la evaluación técnica general de la velocidad y salud.",
  "principal_riesgo": "1 frase detallando el mayor riesgo detectado en el sprint.",
  "recomendacion_lider": "1 frase con la acción prioritaria para el Scrum Master o Líder Técnico."
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
    Mantiene una conversación fluida e inteligente con el usuario basada en datos reales de MCHAV y Jira.
    """
    if not is_gemini_configured():
        return (
            "🤖 *Modo Conversativo Local*: No he detectado una `GEMINI_API_KEY` activa en el archivo `.env`. "
            "Para chatear en tiempo real con la IA de Google Gemini (gemini-2.5-flash), configura tu API Key en el `.env` del backend."
        )

    context_info = context_info or {}
    proj_id = context_info.get("id_proyecto", "PROJ-01")
    user_name = context_info.get("user_name", "Usuario")
    health = context_info.get("health_score", 85)
    cycle_time = context_info.get("cycle_time", 2.5)
    wip = context_info.get("wip", 3)

    history_str = ""
    if conversation_history:
        for msg in conversation_history[-4:]: # Últimos 4 mensajes
            role = "Usuario" if msg.get("sender") == "user" else "AI Coach"
            history_str += f"{role}: {msg.get('text', '')}\n"

    prompt = f"""
Eres el 'AI Dev Coach & Asistente Inteligente de MCHAV Analytics', una IA empática, amigable, sabia y experta en agilidad de software, Scrum, métricas de Jira (Cycle Time, Throughput, WIP, Lead Time) y rendimiento de equipos.

Contexto actual del proyecto y usuario ({user_name}):
- Proyecto activo: {proj_id}
- Salud del Sprint: {health}/100 pts.
- Tiempo de ciclo promedio: {cycle_time} días.
- Tareas en progreso (WIP): {wip}.

Historial reciente de la conversación:
{history_str}

Pregunta o mensaje actual del usuario ({user_name}):
"{user_message}"

Instrucciones de respuesta:
1. Responde de forma amigable, directa, profesional y conversacional en español.
2. Utiliza viñetas breves o emojis oportunos (🦉, ⚡, 📊, 💡) para hacer la lectura ágil.
3. Si la pregunta concierne a métricas o consejos de desarrollo, fundamenta tu respuesta en principios de flujo continuo y reducción de WIP.
4. Mantén la respuesta concisa y clara (máximo 2 a 3 párrafos cortos).
"""

    reply = _call_gemini_rest_api(prompt, temperature=0.6, max_tokens=450)
    if reply:
        return reply

    return "Disculpa, en este momento no pude consultar el motor de Gemini. Por favor verifica la conexión a Internet o inténtalo nuevamente en unos segundos."
