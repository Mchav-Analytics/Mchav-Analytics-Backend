# MCHAV Analytics

Monorepo con backend (FastAPI) y frontend (React) para métricas, sincronización Jira y dashboard operativo.

## Estructura

```text
backend/
  app/              API, servicios, modelos ORM y seeds
  alembic/          Migraciones de base de datos
  tests/            Pruebas pytest
  Dockerfile
  requirements.txt
frontend/
  src/              Dashboard, auth y cliente API
docker-compose.yml  Backend + PostgreSQL
```

## Levantar entorno (sin Python local)

```powershell
# 1. Crear .env en la raíz del repo
copy backend\.env.example .env

# 2. Levantar servicios
docker compose up -d --build

# 3. Migraciones
docker compose exec backend alembic upgrade head

# 4. Datos iniciales
docker compose exec backend python -m app.seeds

# 5. Probar salud
curl http://localhost:8080/health
```

## Frontend

```powershell
cd frontend
npm install
npm run dev
```

El dev server corre en `http://localhost:3000` y hace proxy de `/api` hacia el backend en `:8080`.

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
cd frontend
npm test
```

## Variables de entorno críticas

El archivo `.env` vive en la raíz del repo (lo lee `docker-compose.yml`).

- `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN` → conexión técnica a Jira
- `JIRA_CLIENT_ID`, `JIRA_CLIENT_SECRET` → OAuth de usuarios
- `DB_*` → PostgreSQL

## Notas de arquitectura

- OAuth identifica usuarios (JWT interno).
- API Token admin consulta y sincroniza Jira de forma centralizada.
- Los KPIs se calculan sobre datos locales (`issues`, `sprints`) para no depender de Jira en cada vista.
