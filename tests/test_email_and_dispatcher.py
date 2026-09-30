import pytest
from unittest.mock import MagicMock, patch
from app.services.email_service import send_email
from app.services.monthly_report_dispatcher_service import (
    _build_admin_email_html,
    _build_leader_email_html,
    dispatch_monthly_reports
)
import app.models as models

def test_send_email_no_credentials():
    with patch("app.services.email_service.MAIL_USERNAME", None), \
         patch("app.services.email_service.MAIL_PASSWORD", None):
        res = send_email("test@example.com", "Asunto", "<p>Hola</p>")
        assert res is False

def test_send_email_success_with_attachment():
    with patch("app.services.email_service.MAIL_USERNAME", "admin@example.com"), \
         patch("app.services.email_service.MAIL_PASSWORD", "secret123"), \
         patch("smtplib.SMTP") as mock_smtp:
        
        instance = MagicMock()
        mock_smtp.return_value.__enter__.return_value = instance
        
        res = send_email(
            to_email="user@example.com",
            subject="Reporte Mensual",
            html_content="<p>Reporte en PDF adjunto</p>",
            attachment_bytes=b"%PDF-1.4 dummy",
            attachment_filename="reporte.pdf"
        )
        assert res is True
        instance.starttls.assert_called_once()
        instance.login.assert_called_once_with("admin@example.com", "secret123")
        instance.send_message.assert_called_once()

def test_send_email_smtp_exception():
    with patch("app.services.email_service.MAIL_USERNAME", "admin@example.com"), \
         patch("app.services.email_service.MAIL_PASSWORD", "secret123"), \
         patch("smtplib.SMTP", side_effect=Exception("SMTP Connection failed")):
        
        res = send_email("user@example.com", "Test", "<p>Error</p>")
        assert res is False

def test_build_email_html():
    admin_html = _build_admin_email_html("Carlos")
    assert "Carlos" in admin_html
    assert "Reporte Mensual" in admin_html

    leader_html = _build_leader_email_html("Ana", "Proyecto Alfa")
    assert "Ana" in leader_html
    assert "Proyecto Alfa" in leader_html

def test_dispatch_monthly_reports():
    mock_db = MagicMock()
    proj = MagicMock()
    proj.id_proyecto = "PROJ-TEST"
    proj.nombre = "Proyecto Test"
    proj.estado = "Active"

    mock_db.query.return_value.all.return_value = [proj]

    user = MagicMock()
    user.nombre = "Valentina Montalvo"
    user.email = "valentina@example.com"
    mock_db.query.return_value.filter.return_value.first.return_value = user

    with patch("app.services.monthly_report_dispatcher_service.generate_pdf_report_bytes", return_value=b"%PDF-report"), \
         patch("app.services.monthly_report_dispatcher_service.send_email", return_value=True) as mock_send:
        
        res = dispatch_monthly_reports(mock_db, target_email="valentina@example.com")
        assert res["status"] == "success"
        assert mock_send.call_count == 2
