# app/core/config.py
# Módulo de configuración global del sistema
# Carga variables de entorno desde el archivo .env y expone constantes tipadas

import os
from pathlib import Path
from dotenv import load_dotenv

# Cargar variables de entorno asegurando la ruta absoluta del archivo .env
BASE_DIR = Path(__file__).resolve().parent.parent.parent
env_path = BASE_DIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path, override=True)
else:
    load_dotenv(override=True)

# -----------------------------------------------------------------------------
# CREDENTCIALES DE AUTENTICACIÓN JIRA OAUTH 2.0 (3LO)
# -----------------------------------------------------------------------------
# Identificador único del cliente registrado en Atlassian Developer Console
CLIENT_ID = os.getenv("JIRA_CLIENT_ID", "").strip() or os.getenv("ATLASSIAN_CLIENT_ID", "").strip()

# Clave secreta del cliente OAuth para intercambiar códigos de autorización
CLIENT_SECRET = os.getenv("JIRA_CLIENT_SECRET", "").strip() or os.getenv("ATLASSIAN_CLIENT_SECRET", "").strip()

# URL de redirección (Callback) donde Atlassian enviará el código de autorización
CALLBACK_URL = os.getenv("JIRA_CALLBACK_URL", "").strip() or os.getenv("ATLASSIAN_REDIRECT_URI", "").strip()

# Clave secreta para la firma criptográfica HMAC SHA-256 de cookies de sesión
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "mchav_default_secret_key_123456").encode()

# URL del Frontend (React/Vite) permitida para políticas CORS
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").strip()

DATABASE_URL = os.getenv("DATABASE_URL") or "sqlite:///./mchav.db"

# -----------------------------------------------------------------------------
# CREDENCIALES DE API TOKEN DE JIRA (FALLBACK DEL SISTEMA Y BASIC AUTH)
# -----------------------------------------------------------------------------
# Dominio base de Jira Cloud (ejemplo: https://mi-empresa.atlassian.net)
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN", "").strip()

# Correo electrónico de la cuenta con permisos de administrador en Jira
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "").strip()

# Token de API generado en la consola de Atlassian para acceso programático
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "").strip()

# -----------------------------------------------------------------------------
# CREDENCIALES E INTEGRACIÓN DE GOOGLE GEMINI API (IA GENERATIVA)
# -----------------------------------------------------------------------------
# API Key del proyecto de Google Gemini (Plan Pro o Developer Console)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip() or os.getenv("GOOGLE_API_KEY", "").strip()

# Modelo predeterminado de alta velocidad y eficiencia
GEMINI_MODEL_NAME = os.getenv("GEMINI_MODEL_NAME", "gemini-flash-lite-latest").strip()

# -----------------------------------------------------------------------------
# SESIÓN Y COOKIES DE AUTENTICACIÓN DE USUARIO
# -----------------------------------------------------------------------------
# Nombre de la cookie HTTP-Only donde se almacena el ID de usuario firmado (HMAC).
# DEBE coincidir con el nombre usado en response.set_cookie(...) al hacer login.
SESSION_COOKIE_NAME = os.getenv("SESSION_COOKIE_NAME", "session_id").strip()

# -----------------------------------------------------------------------------
# SEGURIDAD Y PROTECCIÓN DE LA DOCUMENTACIÓN OPENAPI / SWAGGER (/docs)
# -----------------------------------------------------------------------------
# Usuario para acceder a la documentación interactiva Swagger/ReDoc
DOCS_USER = os.getenv("DOCS_USER", "admin").strip()

# Contraseña para la autenticación HTTP Basic de la documentación
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "MchavDocs2026!Sec#Admin").strip()

# -----------------------------------------------------------------------------
# GOOGLE GEMINI AI
# -----------------------------------------------------------------------------
# Clave de API para el modelo generativo de Google Gemini (AI Dev Coach)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()