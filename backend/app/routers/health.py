from fastapi import APIRouter

from app.database import check_db_connection

router = APIRouter(tags=["Health"])


@router.get("/health")
async def health_check():
    db_ok = check_db_connection()
    return {
        "status": "ok" if db_ok else "degraded",
        "database": "ok" if db_ok else "unavailable",
    }
