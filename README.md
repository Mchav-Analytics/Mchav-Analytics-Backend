# MCHAV Analytics — Backend

Capa intermedia sobre Jira para métricas, sincronización y calidad operativa.

## Stack

- FastAPI + Uvicorn
- PostgreSQL + SQLAlchemy + Alembic
- Docker Compose (no requiere Python instalado en tu PC)

## Estructura

```text
app/
  core/           Configuración y excepciones
  routers/        Endpoints HTTP (auth, jira, projects, kpis, admin)
  schemas/        Contratos Pydantic para Swagger
  services/       Lógica de negocio (jira, sync, kpi, auth)
    mappers/      Transformación JSON Jira -> modelos locales
  features/jira/models/   Modelos ORM
  seeds/          Datos iniciales (roles, KPIs, admin)
tests/            Pruebas unitarias e integración ligera
```

## Levantar entorno (sin Python local)

```powershell
# 1. Crear .env desde .env.example
copy .env.example .env

# 2. Levantar servicios
docker compose up -d --build

# 3. Migraciones
docker compose exec backend alembic upgrade head

# 4. Datos iniciales
docker compose exec backend python -m app.seeds

# 5. Probar salud
curl http://localhost:8080/health
```

## Endpoints principales

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/api/auth/login` | Inicia OAuth con Atlassian |
| GET | `/api/auth/callback` | Callback OAuth |
| POST | `/api/auth/logout` | Cierra sesión |
| GET | `/api/jira/proyecto/{key}` | Proyecto en vivo desde Jira |
| POST | `/api/jira/search` | Ejecuta JQL contra Jira |
| GET | `/api/jira/metrics/open-issues/{key}` | Conteo de issues abiertos |
| GET | `/api/projects` | Proyectos persistidos en MCHAV |
| POST | `/api/projects/sync` | Sincroniza proyecto Jira -> BD (admin) |
| GET | `/api/kpis/sprints/{id}` | KPIs calculados de un sprint |
| POST | `/api/kpis/sprints/{id}/compute` | Recalcula KPIs del sprint |
| GET | `/docs` | Swagger UI |

## Flujo recomendado

1. Login OAuth y obtener JWT.
2. `POST /api/projects/sync` con `{ "project_key": "SCRUM" }`.
3. `POST /api/kpis/sprints/{id}/compute`.
4. `GET /api/kpis/sprints/{id}` para consumir desde frontend.

## Pruebas

```powershell
docker compose exec backend pytest -q
```

## Variables de entorno críticas

- `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` → conexión técnica a Jira
- `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET` → OAuth de usuarios
- `DB_*` → PostgreSQL

## Notas de arquitectura

- OAuth identifica usuarios (JWT interno).
- API Token admin consulta y sincroniza Jira de forma centralizada.
- Los KPIs se calculan sobre datos locales (`issues`, `sprints`) para no depender de Jira en cada vista.
