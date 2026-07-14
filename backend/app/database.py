from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import text

from app.core.config import settings

# 1. URL de conexión centralizada en app.core.config
DATABASE_URL = settings.DATABASE_URL
# 2. Motor de la base de datos
engine = create_engine(DATABASE_URL)

# 3. Fábrica de sesiones para los endpoints
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 4. Base declarativa que heredan todos tus modelos
Base = declarative_base()

# 5. Función de control para tu health-check en main.py
def check_db_connection() -> bool:
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
            return True
    except Exception:
        return False

# 6. Dependencia para los futuros endpoints de FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()