import pytest
from unittest.mock import patch, MagicMock
from app.services.gemini_service import (
    is_gemini_configured,
    _call_gemini_rest_api,
    generate_dev_coach_tip,
    generate_lider_dashboard_insights,
    generate_pdf_conclusions,
    chat_with_gemini,
    gemini_cache
)

def test_is_gemini_configured():
    with patch("app.services.gemini_service.GEMINI_API_KEY", "valid_key_1234567890"):
        assert is_gemini_configured() is True
    with patch("app.services.gemini_service.GEMINI_API_KEY", ""):
        assert is_gemini_configured() is False

def test_call_gemini_rest_api_not_configured():
    with patch("app.services.gemini_service.is_gemini_configured", return_value=False):
        assert _call_gemini_rest_api("test prompt") is None

def test_call_gemini_rest_api_success():
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_res.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Respuesta Gemini"}]}}]
    }
    
    mock_client = MagicMock()
    mock_client.post.return_value = mock_res
    
    with patch("app.services.gemini_service.is_gemini_configured", return_value=True), \
         patch("httpx.Client") as mock_httpx:
        mock_httpx.return_value.__enter__.return_value = mock_client
        res = _call_gemini_rest_api("prompt")
        assert res == "Respuesta Gemini"

def test_generate_dev_coach_tip():
    scorecard = {"email": "test@dev.com", "cycle_time_personal": 2.5}
    fallback = "Consejo por defecto"
    
    # 1. Test fallback when not configured
    with patch("app.services.gemini_service.is_gemini_configured", return_value=False):
        tip = generate_dev_coach_tip(scorecard, [], [], fallback)
        assert tip == fallback

    # 2. Test cached value
    gemini_cache.set("gemini_dev_tip_test@dev.com", "Consejo cacheado")
    tip_cached = generate_dev_coach_tip(scorecard, [], [], fallback)
    assert tip_cached == "Consejo cacheado"

def test_generate_lider_dashboard_insights():
    health = {"id_proyecto": "P-TEST", "health_score": 85}
    fallback = {"diagnostico_ejecutivo": "Fallback"}
    
    # Fallback when not configured
    with patch("app.services.gemini_service.is_gemini_configured", return_value=False):
        res = generate_lider_dashboard_insights(health, [], fallback)
        assert res == fallback

    # Valid JSON response
    with patch("app.services.gemini_service.is_gemini_configured", return_value=True), \
         patch("app.services.gemini_service._call_gemini_rest_api", return_value='{"diagnostico_ejecutivo": "OK"}'):
        res_ok = generate_lider_dashboard_insights(health, [], fallback)
        assert res_ok.get("diagnostico_ejecutivo") == "OK"

def test_generate_pdf_conclusions():
    with patch("app.services.gemini_service.is_gemini_configured", return_value=False):
        res_fb = generate_pdf_conclusions("PROJ", 2.0, 10, 20.0)
        assert "PROJ" in res_fb

    with patch("app.services.gemini_service.is_gemini_configured", return_value=True), \
         patch("app.services.gemini_service._call_gemini_rest_api", return_value="Conclusión PDF"):
        res_ok = generate_pdf_conclusions("PROJ", 2.0, 10, 20.0)
        assert res_ok == "Conclusión PDF"

def test_chat_with_gemini():
    with patch("app.services.gemini_service.is_gemini_configured", return_value=False):
        res_local = chat_with_gemini("Hola")
        assert "Modo Conversacional Local" in res_local

    with patch("app.services.gemini_service.is_gemini_configured", return_value=True), \
         patch("app.services.gemini_service._call_gemini_rest_api", return_value="Respuesta del Chat"):
        res_chat = chat_with_gemini("Hola", context_info={"user_name": "Mike"})
        assert res_chat == "Respuesta del Chat"
