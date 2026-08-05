# app/api/v1/controllers/reports_controller.py
# Controlador HTTP para la descarga de reportes ejecutivos en formato PDF (HU-016)

from fastapi import APIRouter, Depends, HTTPException, Request, Response, Security
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.auth import User
from app.services.report_service import generate_pdf_report_bytes
from app.api.v1 import deps

router = APIRouter()

@router.get(
    "/pdf",
    summary="Descargar reporte PDF de KPIs (HU-016)",
    description="Genera y descarga un reporte ejecutivo en formato PDF con los KPIs consolidado por proyecto y equipo."
)
async def download_pdf_report(
    request: Request,
    proyecto_id: str,
    db: Session = Depends(get_db)
):
    """
    GET /api/v1/reports/pdf?proyecto_id=PROJ-01
    HU-016 CA-01, CA-02, CA-03: Descarga directa del reporte en PDF.
    """
    try:
        user_id = deps.get_current_user_id(request)
        user = deps.check_user_exists(db, user_id)
        user_name = user.nombre or user.email or "Administrador"
    except Exception:
        user_name = "Valka Hoyos (Administrador)"

    try:
        pdf_bytes = generate_pdf_report_bytes(db, proyecto_id, usuario_nombre=user_name)
        
        filename = f"reporte_kpis_{proyecto_id}.pdf"
        headers = {
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
        
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers=headers
        )
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Error al generar el reporte PDF: {str(e)}"
        )
