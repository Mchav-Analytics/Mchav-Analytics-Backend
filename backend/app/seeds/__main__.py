import os

from app.db.session import SessionLocal
from app.seeds.run_seed import run_all

if __name__ == "__main__":
    db = SessionLocal()
    try:
        run_all(
            db,
            admin_email=os.getenv("SEED_ADMIN_EMAIL", "corredorbeltran592@gmail.com"),
            admin_name=os.getenv("SEED_ADMIN_NAME", "Camilo Corredor"),
            admin_password=os.getenv("SEED_ADMIN_PASSWORD", "Admin123!"),
        )
        print("Seed completado.")
    finally:
        db.close()
