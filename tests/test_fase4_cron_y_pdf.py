# tests/test_fase4_cron_y_pdf.py
# Pruebas automatizadas para la Fase 4: Cron Scheduler y Generación de Reportes PDF (HU-010, HU-016)

import pytest
from unittest.mock import MagicMock, patch
from app.services.report_service import generate_pdf_report_bytes
from app.core.scheduler import start_scheduler, stop_scheduler

def test_generacion_bytes_pdf_reporte():
    """HU-016 CA-01: Probar la generación del documento PDF retornando cabecera de archivo %PDF-"""
    mock_db = MagicMock()
    mock_db.query().filter().order_by().limit().all.return_value = []
    mock_db.query().filter().all.return_value = []
    
    pdf_bytes = generate_pdf_report_bytes(mock_db, proyecto_id="PROJ-01", usuario_nombre="Usuario Prueba")
    
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 0
    assert pdf_bytes.startswith(b"%PDF-")

def test_inicializacion_cron_scheduler():
    """HU-010 CA-01: Probar el arranque e interrupción segura del planificador APScheduler"""
    with patch("app.core.scheduler.BackgroundScheduler") as mock_sched_class:
        mock_sched_instance = MagicMock()
        mock_sched_class.return_value = mock_sched_instance
        
        start_scheduler()
        assert mock_sched_instance.add_job.called
        assert mock_sched_instance.start.called
        
        stop_scheduler()
