from app.database import SessionLocal
from app.seeds.run_seed import run_all

if __name__ == "__main__":
    db = SessionLocal()
    try:
        run_all(
            db,
            admin_email="admin@grupoasd.com",
            admin_name="Administrador MCHAV",
        )
        print("Seed completado.")
    finally:
        db.close()
