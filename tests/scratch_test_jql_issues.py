import asyncio
import httpx
from app.core.database import SessionLocal
from app.services.jql_service import execute_jql
import json

db = SessionLocal()

async def test():
    # Execute JQL bypasses auth if we mock user
    try:
        from app.models.auth import Usuario
        user = db.query(Usuario).first()
        res = await execute_jql(db, user, "project = \"10000\" AND status != \"Done\" ORDER BY priority DESC, created DESC", 10)
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(e)
    finally:
        db.close()

asyncio.run(test())
