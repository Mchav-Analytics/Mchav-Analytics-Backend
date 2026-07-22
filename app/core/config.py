import os
from dotenv import load_dotenv

load_dotenv(override=True)

CLIENT_ID = os.getenv("JIRA_CLIENT_ID", "").strip()
CLIENT_SECRET = os.getenv("JIRA_CLIENT_SECRET", "").strip()
CALLBACK_URL = os.getenv("JIRA_CALLBACK_URL", "").strip()
SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "mchav_default_secret_key_123456").encode()
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173").strip()
DATABASE_URL = os.getenv("DATABASE_URL")

# Credenciales de API Token de Jira (Fallback del Sistema)
JIRA_DOMAIN = os.getenv("JIRA_DOMAIN", "").strip()
JIRA_EMAIL = os.getenv("JIRA_EMAIL", "").strip()
JIRA_API_TOKEN = os.getenv("JIRA_API_TOKEN", "").strip()

# Credenciales de protección HTTP Basic Auth para la documentación (/docs)
DOCS_USER = os.getenv("DOCS_USER", "admin").strip()
DOCS_PASSWORD = os.getenv("DOCS_PASSWORD", "MchavDocs2026!Sec#Admin").strip()
