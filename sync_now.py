import os
import sys
sys.path.append(os.getcwd())

from app.core.database import SessionLocal
from app.services.jira_sync_service import run_jira_sync_task
from app.models.auth import User

def main():
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id_usuario == 3).first()
        if not user:
            print("User 3 not found, using first user")
            user = db.query(User).first()
        if not user:
            print("No users found in database")
            return
            
        print(f"Running sync task for user: {user.email}")
        run_jira_sync_task(user.id_usuario)
        print("Sync complete!")
    finally:
        db.close()

if __name__ == "__main__":
    main()
