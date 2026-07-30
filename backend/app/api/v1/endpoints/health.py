"""Health check del servicio."""

from fastapi import APIRouter

from app.db.session import check_db_connection

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    response_model=dict,
    summary="Estado del servicio y de la base de datos",
)
async def health_check():
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unavailable",
    }
