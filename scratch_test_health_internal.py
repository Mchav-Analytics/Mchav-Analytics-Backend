from app.core.database import SessionLocal
from app.services.sprint_health_service import calculate_sprint_health

db = SessionLocal()
res = calculate_sprint_health(db, "10000", "117")
import json
print(json.dumps(res, indent=2))
db.close()
