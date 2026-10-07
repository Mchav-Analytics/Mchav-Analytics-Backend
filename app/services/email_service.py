# app/services/email_service.py
# Servicio de envío de correos electrónicos vía SMTP (Gmail)
# Soporta cuerpo formateado en HTML y archivos adjuntos (PDF)

import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from typing import Optional, List, Tuple

from app.core.config import (
    MAIL_SERVER,
    MAIL_PORT,
    MAIL_USERNAME,
    MAIL_PASSWORD,
    MAIL_FROM,
    MAIL_FROM_NAME
)

logger = logging.getLogger(__name__)


def send_email(
    to_email: str,
    subject: str,
    html_content: str,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: Optional[str] = None,
    attachments: Optional[List[Tuple[bytes, str]]] = None
) -> bool:
    """
    Envía un correo electrónico individual con cuerpo HTML y adjunto opcional (PDF).
    Retorna True si el envío fue exitoso, o False si ocurrió algún error.
    """
    if not MAIL_USERNAME or not MAIL_PASSWORD:
        logger.error("[EmailService] No se configuraron credenciales MAIL_USERNAME / MAIL_PASSWORD en el archivo .env")
        return False

    try:
        msg = MIMEMultipart()
        msg['From'] = f"{MAIL_FROM_NAME} <{MAIL_FROM or MAIL_USERNAME}>"
        msg['To'] = to_email
        msg['Subject'] = subject

        # Adjuntar el cuerpo del correo formateado en HTML
        msg.attach(MIMEText(html_content, 'html', 'utf-8'))

        # Adjuntar archivos PDF (uno o varios)
        all_attachments = list(attachments or [])
        if attachment_bytes and attachment_filename:
            all_attachments.insert(0, (attachment_bytes, attachment_filename))
        for file_bytes, file_name in all_attachments:
            if not file_bytes or not file_name:
                continue
            part = MIMEApplication(file_bytes, Name=file_name)
            part['Content-Disposition'] = f'attachment; filename="{file_name}"'
            msg.attach(part)

        # Establecer conexión TLS con el servidor SMTP de Gmail (puerto 587)
        with smtplib.SMTP(MAIL_SERVER, MAIL_PORT, timeout=30) as server:
            server.starttls()
            server.login(MAIL_USERNAME, MAIL_PASSWORD)
            server.send_message(msg)

        logger.info(f"[EmailService] Correo enviado exitosamente a: {to_email}")
        return True

    except Exception:
        logger.exception(f"[EmailService] Error enviando correo a {to_email}")
        return False
