# app/services/monthly_report_dispatcher_service.py
# Servicio de consolidación y despacho de reportes mensuales ejecutivos con Nubi AI (Gemini)

import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

import app.models as models
from app.services.email_service import send_email
from app.services.report_service import generate_pdf_report_bytes
from app.services.gemini_service import generar_analisis_ejecutivo_nubi

logger = logging.getLogger(__name__)

def _build_admin_email_html(admin_name: str) -> str:
    """Genera el cuerpo del correo como una notificación breve (sin el contenido del reporte)."""
    date_str = datetime.now().strftime("%B de %Y")
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: 'Segoe UI', Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.6; background-color: #f8fafc; padding: 20px;">
        <div style="max-width: 580px; margin: 0 auto; background: #ffffff; padding: 32px; border-radius: 12px; border: 1px solid #cbd5e1; box-shadow: 0 4px 6px rgba(0,0,0,0.04);">
            <p style="font-size: 15px; margin-top: 0; color: #0f172a;">Hola <strong>{admin_name}</strong>,</p>
            <p style="font-size: 14px; color: #334155;">
                Se ha generado el <strong>Reporte Mensual de Rendimiento de Portafolio</strong> correspondiente a <strong>{date_str}</strong>.
            </p>
            <p style="font-size: 14px; color: #334155;">
                En el archivo PDF adjunto encontrarás el reporte completo con el análisis de métricas, evolución de los proyectos, riesgos y recomendaciones generadas por Nubi IA.
            </p>
            <br>
            <p style="font-size: 14px; margin-bottom: 0; color: #475569;">
                Saludos,<br>
                <strong style="color: #4f46e5;">MCHAV Analytics</strong>
            </p>
        </div>
    </body>
    </html>
    """


def _build_leader_email_html(leader_name: str, project_name: str) -> str:
    """Genera el cuerpo del correo de notificación para Líder Técnico."""
    date_str = datetime.now().strftime("%B de %Y")
    return f"""
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
    </head>
    <body style="font-family: 'Segoe UI', Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.6; background-color: #f8fafc; padding: 20px;">
        <div style="max-width: 580px; margin: 0 auto; background: #ffffff; padding: 32px; border-radius: 12px; border: 1px solid #cbd5e1; box-shadow: 0 4px 6px rgba(0,0,0,0.04);">
            <p style="font-size: 15px; margin-top: 0; color: #0f172a;">Hola <strong>{leader_name}</strong>,</p>
            <p style="font-size: 14px; color: #334155;">
                Se ha generado el <strong>Reporte Mensual del Proyecto ({project_name})</strong> correspondiente a <strong>{date_str}</strong>.
            </p>
            <p style="font-size: 14px; color: #334155;">
                En el archivo PDF adjunto encontrarás el reporte completo con el análisis de métricas, avance planificado vs completado, salud del equipo y diagnósticos de Nubi IA.
            </p>
            <br>
            <p style="font-size: 14px; margin-bottom: 0; color: #475569;">
                Saludos,<br>
                <strong style="color: #0284c7;">MCHAV Analytics</strong>
            </p>
        </div>
    </body>
    </html>
    """


def dispatch_monthly_reports(db: Session, target_email: Optional[str] = None) -> Dict[str, Any]:
    """
    Consolida métricas, ejecuta diagnósticos de Nubi AI (Gemini), genera los reportes PDF
    y despacha los correos a Administradores y Líderes Técnicos.
    """
    logger.info("[MonthlyReportDispatcher] Iniciando proceso de despacho de reportes mensuales...")

    proyectos = db.query(models.Proyecto).all()
    proyectos_activos = [p for p in proyectos if p.estado == 'Active'] or proyectos
    first_proj_id = proyectos_activos[0].id_proyecto if (proyectos_activos and hasattr(proyectos_activos[0], 'id_proyecto') and proyectos_activos[0].id_proyecto) else "PROJ-01"
    proj_name = proyectos_activos[0].nombre if proyectos_activos else "MCHAV Analytics"

    # Generación física del archivo PDF oficial completo (con las gráficas de Matplotlib del Centro de Reportes)
    pdf_bytes = generate_pdf_report_bytes(db, proyecto_id=first_proj_id, usuario_nombre="Administrador")

    sent_admin_count = 0
    sent_leader_count = 0
    mes_str = datetime.now().strftime("%B_%Y")
    
    pdf_filename_admin = f"Reporte_MCHAV_Analytics_Admin_{mes_str}.pdf"
    pdf_filename_leader = f"Reporte_Proyecto_{proj_name.replace(' ', '_')}_{mes_str}.pdf"

    # Destinatario de prueba / revisión (ÚNICAMENTE valentina1025m@gmail.com o el target_email explícito)
    recipient_email = target_email or "valentina1025m@gmail.com"
    target_user = db.query(models.User).filter(models.User.email.ilike(recipient_email)).first()
    target_name = target_user.nombre if target_user else "Valentina Montalvo"

    # 1. Enviar correo de notificación Admin con PDF adjunto
    html_admin = _build_admin_email_html(admin_name=target_name)
    if send_email(recipient_email, f"📊 Reporte Mensual de Rendimiento de Portafolio - {datetime.now().strftime('%B %Y')}", html_admin, pdf_bytes, pdf_filename_admin):
        sent_admin_count += 1

    # 2. Enviar correo de notificación Líder con PDF adjunto
    html_leader = _build_leader_email_html(leader_name=target_name, project_name=proj_name)
    if send_email(recipient_email, f"🚀 Reporte Mensual de Proyecto ({proj_name}) - MCHAV Analytics", html_leader, pdf_bytes, pdf_filename_leader):
        sent_leader_count += 1

    logger.info(f"[MonthlyReportDispatcher] Proceso finalizado. Correos enviados a {recipient_email}: Admins ({sent_admin_count}), Líderes ({sent_leader_count})")

    return {
        "status": "success",
        "timestamp": datetime.now().isoformat(),
        "recipient": recipient_email,
        "admins_notified": sent_admin_count,
        "leaders_notified": sent_leader_count,
        "total_sent": sent_admin_count + sent_leader_count
    }

