# app/core/database.py
# Módulo de conexión y gestión de sesiones de la Base de Datos (SQLAlchemy)

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL

# Crear motor de conexión principal usando la URL configurada en DATABASE_URL
engine = create_engine(DATABASE_URL)

# Fábrica de sesiones ORM individuales para cada petición HTTP
# autocommit=False: Requiere un commit explícito para confirmar transacciones
# autoflush=False: Previene descargas automáticas antes de completar consultas complejas
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Clase base declarativa para la definición de todos los modelos ORM de la base de datos
Base = declarative_base()

def get_db():
    """
    Generador de dependencia de FastAPI que provee una sesión de base de datos aislada.
    Garantiza que la sesión se cierre correctamente al finalizar cada petición HTTP.
    """
    db = SessionLocal()  # Crear nueva sesión para la petición
    try:
        yield db         # Inyectar la sesión en el endpoint o controlador
    finally:
        db.close()       # Cerrar la sesión de manera segura para liberar conexiones del pool
