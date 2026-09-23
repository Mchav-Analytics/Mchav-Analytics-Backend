import pytest
from unittest.mock import MagicMock, patch
import app.services.gemini_service as gs

def test_is_gemini_configured():
    with patch.object(gs, "GEMINI_API_KEY", "AIzaSyFakeKey123456789"):
        assert gs.is_gemini_configured() is True
    with patch.object(gs, "GEMINI_API_KEY", ""):
        assert gs.is_gemini_configured() is False

def test_call_gemini_rest_api_not_configured():
    with patch.object(gs, "GEMINI_API_KEY", ""):
        res = gs._call_gemini_rest_api("Hola")
        assert res is None

def test_call_gemini_rest_api_success():
    with patch.object(gs, "GEMINI_API_KEY", "AIzaSyFakeKey123456789"):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Respuesta simulada de Gemini"}]
                    }
                }
            ]
        }
        with patch("httpx.Client.post", return_value=mock_response):
            res = gs._call_gemini_rest_api("Explica el cycle time")
            assert res == "Respuesta simulada de Gemini"

def test_call_gemini_rest_api_fallback_and_error():
    with patch.object(gs, "GEMINI_API_KEY", "AIzaSyFakeKey123456789"):
        resp_404 = MagicMock(status_code=404)
        resp_500 = MagicMock(status_code=500, text="Internal Error")
        
        with patch("httpx.Client.post", side_effect=[resp_404, resp_500, Exception("Network timeout")]):
            res = gs._call_gemini_rest_api("Prompt")
            assert res is None

def test_generate_dev_coach_tip():
    scorecard = {
        "email": "dev@test.com",
        "cycle_time_personal": 2.5,
        "cycle_time_prev": 3.0,
        "wip_tickets": 2,
        "throughput_tickets": 8,
        "clean_deliveries_pct": 90
    }
    urgent_qa = [{"key_issue": "BUG-1"}]
    fallback = "Consejo por defecto"

    # Test cache hit
    gs.gemini_cache.set("gemini_dev_tip_dev@test.com", "Consejo en cache")
    assert gs.generate_dev_coach_tip(scorecard, urgent_qa, [], fallback) == "Consejo en cache"

    # Test without config
    gs.gemini_cache.clear()
    with patch.object(gs, "is_gemini_configured", return_value=False):
        assert gs.generate_dev_coach_tip(scorecard, urgent_qa, [], fallback) == fallback

    # Test with API call
    with patch.object(gs, "is_gemini_configured", return_value=True), \
         patch.object(gs, "_call_gemini_rest_api", return_value="Excelente ritmo de entrega"):
        tip = gs.generate_dev_coach_tip(scorecard, urgent_qa, [], fallback)
        assert tip == "Excelente ritmo de entrega"

def test_generate_lider_dashboard_insights():
    health = {"salud_general": "SALUDABLE", "desglose": {}}
    alerts = [{"tipo": "BLOQUEO", "mensaje": "Alerta crítica"}]
    fallback = {"diagnostico": "Todo en orden"}

    # Fallback when not configured
    with patch.object(gs, "is_gemini_configured", return_value=False):
        res = gs.generate_lider_dashboard_insights(health, alerts, fallback)
        assert res == fallback

    # Success parsing JSON
    with patch.object(gs, "is_gemini_configured", return_value=True), \
         patch.object(gs, "_call_gemini_rest_api", return_value='```json\n{"diagnostico": "Excelente estado", "recomendacion": "Mantener WIP"}\n```'):
        res = gs.generate_lider_dashboard_insights(health, alerts, fallback)
        assert res["diagnostico"] == "Excelente estado"

def test_generate_pdf_conclusions_and_executive_analysis():
    with patch.object(gs, "is_gemini_configured", return_value=True), \
         patch.object(gs, "_call_gemini_rest_api", return_value="Conclusiones ejecutivas"):
        c = gs.generate_pdf_conclusions("MCHAV", 3.2, 15, 45.0)
        assert "Conclusiones" in c

        a = gs.generar_analisis_ejecutivo_nubi("Contexto del proyecto")
        assert "Conclusiones" in a

    # Fallbacks when API returns None
    with patch.object(gs, "is_gemini_configured", return_value=True), \
         patch.object(gs, "_call_gemini_rest_api", return_value=None):
        c_fall = gs.generate_pdf_conclusions("MCHAV", 3.2, 15, 45.0)
        assert len(c_fall) > 0
        a_fall = gs.generar_analisis_ejecutivo_nubi("Contexto")
        assert len(a_fall) > 0

def test_chat_with_gemini():
    with patch.object(gs, "is_gemini_configured", return_value=True), \
         patch.object(gs, "_call_gemini_rest_api", return_value="Respuesta a usuario"):
        reply = gs.chat_with_gemini("¿Cómo va el proyecto?", context_info={"nombre": "Alfa"})
        assert reply == "Respuesta a usuario"

    with patch.object(gs, "is_gemini_configured", return_value=False):
        reply = gs.chat_with_gemini("Hola")
        assert "No tengo conexión" in reply or "configurada" in reply or len(reply) > 0

def test_generate_report_insights_and_prompts():
    metrics = {
        "velocity": 20, "throughput": 5, "cycle_time": 3.0,
        "burndown": "al día", "bugs": 1, "scope_changes": 0, "sprint_health": "Bueno",
        "p50": 2, "p85": 4, "p95": 6, "planned_points": 25, "completed_percentage": 90,
        "dev_name": "Juan", "active_projects": 3
    }
    fallback = {"insights": "Default"}

    with patch.object(gs, "is_gemini_configured", return_value=True), \
         patch.object(gs, "_call_gemini_rest_api", return_value="Diagnóstico del reporte"):
        
        # Various report types and leader flags
        for r_type in ["sprint", "proyecto", "desarrollador", "general"]:
            for is_lead in [True, False]:
                res = gs.generate_report_insights(metrics, fallback, report_type=r_type, is_leader=is_lead)
                assert res == "Diagnóstico del reporte"

    # Fallback insights
    for r_type in ["sprint", "proyecto", "desarrollador", "general"]:
        fb = gs._get_fallback_insights(r_type)
        assert len(fb) > 0
