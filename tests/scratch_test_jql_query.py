import asyncio
import httpx
from app.core.database import SessionLocal
from app.models.auth import Usuario
from app.api.v1.controllers.jql_controller import execute_jql_query
from app.schemas.jql import JQLQueryRequest
import json

db = SessionLocal()

async def test():
    try:
        user = db.query(Usuario).first()
        req = JQLQueryRequest(jql="project = \"10000\" AND priority in (High, Highest) AND status != \"Done\"", max_results=10)
        
        # We need to mock request
        class MockRequest:
            pass
            
        import app.api.deps as deps
        original_get_current_user_id = deps.get_current_user_id
        deps.get_current_user_id = lambda r: user.id_usuario
        
        res = await execute_jql_query(MockRequest(), req, db)
        print(json.dumps(res, indent=2))
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()
        
asyncio.run(test())
