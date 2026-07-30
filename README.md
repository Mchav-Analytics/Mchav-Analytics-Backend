# MCHAV Analytics Backend

API FastAPI para sincronización con Jira, persistencia en PostgreSQL y cálculo de KPIs ágiles.

Estructura alineada con la guía [Bigger Applications](https://fastapi.tiangolo.com/tutorial/bigger-applications/) de FastAPI.

## Estructura

```text
backend/
  app/
    main.py           # Entrada FastAPI + lifespan + middlewares
    api/
      router.py       # Agregador de routers
      deps.py         # Dependency Injection
      routes/         # Controllers HTTP por dominio
    core/             # Settings, security, exceptions
    db/               # Engine, sesión, Base ORM
    models/           # Modelos SQLAlchemy
    schemas/          # DTOs Pydantic
    services/         # Lógica de negocio / ETL / KPIs
    seeds/            # Datos iniciales
  alembic/            # Migraciones
  tests/              # Pruebas unitarias e integración ligera
  Dockerfile
  requirements.txt
  requirements-dev.txt
docker-compose.yml    # Backend + PostgreSQL
```

## Levantar entorno

```powershell
copy backend\.env.example .env
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.seeds
curl http://localhost:8080/health
```

Documentación interactiva:

- Swagger UI: http://localhost:8080/docs
- ReDoc: http://localhost:8080/redoc

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Salud del servicio y BD |
| GET | `/api/auth/login` | Inicia OAuth con Atlassian |
| GET | `/api/auth/callback` | Callback OAuth → JWT JSON con scopes |
| POST | `/api/auth/token` | Token para Authorize de `/docs` (OAuth2PasswordBearer) |
| GET | `/api/auth/scopes` | Catálogo de scopes OAuth2 |
| POST | `/api/auth/logout` | Cierra sesión local |
| GET | `/api/jira/proyecto/{key}` | Proyecto en vivo desde Jira (`jira:read`) |
| POST | `/api/jira/search` | Ejecuta JQL (`jira:read`) |
| GET | `/api/projects` | Proyectos persistidos (`projects:read`) |
| POST | `/api/projects/sync` | Sync Jira → BD (`projects:sync`) |
| GET | `/api/kpis/sprints/{id}` | KPIs de un sprint (`kpis:read`) |
| POST | `/api/kpis/sprints/{id}/compute` | Recalcula KPIs (`kpis:compute`) |

## OAuth2 scopes

Integración según [FastAPI OAuth2 scopes](https://fastapi.tiangolo.com/advanced/security/oauth2-scopes/):

| Scope | Permiso |
|-------|---------|
| `me` | Usuario autenticado |
| `projects:read` | Lectura de proyectos/sprints/issues |
| `projects:sync` | Sincronización Jira → BD |
| `jira:read` | Consultas live a Jira |
| `kpis:read` | Lectura de KPIs |
| `kpis:compute` | Cálculo de KPIs |
| `admin` | Endpoints administrativos |

- **Administrador** recibe todos los scopes.
- **Consultor** recibe solo scopes de lectura (`me`, `projects:read`, `jira:read`, `kpis:read`).
- El JWT incluye el claim `scope` (cadena separada por espacios).
- Los endpoints usan `Security(get_current_user, scopes=[...])`.

En `/docs` → **Authorize**: pega el JWT del callback en el campo password.

## Flujo recomendado

1. `GET /api/auth/login` y completar OAuth.
2. Usar el `access_token` Bearer en el resto de endpoints.
3. `POST /api/projects/sync` con `{ "project_key": "SCRUM" }`.
4. `POST /api/kpis/sprints/{id}/compute` y consultar KPIs.

## Pruebas

```powershell
docker compose exec backend pip install -r requirements-dev.txt
docker compose exec backend pytest -q
```

O en local (desde `backend/`):

```powershell
pip install -r requirements-dev.txt
pytest -q
```

## Variables de entorno

Ver `backend/.env.example`. Críticas:

- `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`
- `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET`
- `DB_*`, `JWT_SECRET_KEY`, `SESSION_SECRET_KEY`
- `BACKEND_CORS_ORIGINS`, `AUTH_RETURN_JSON`

## Arquitectura

- OAuth identifica usuarios (JWT interno HS256, 8h).
- API Token admin consulta y sincroniza Jira de forma centralizada (`httpx`).
- KPIs se calculan sobre datos locales para no depender de Jira en cada vista.
- Capas: routes → services → models/db (Dependency Injection).
