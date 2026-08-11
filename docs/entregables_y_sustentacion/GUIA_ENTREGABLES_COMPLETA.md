# Guía Completa de Entregables del Proyecto MCHAV Analytics 📘🎓

Este documento explica **entregable por entregable** cómo se implementó cada tema del syllabus en el proyecto MCHAV Analytics. Está escrito para que cualquier persona nueva pueda abrir este archivo y entender completamente cómo funciona cada pieza del sistema.

---

## 📑 Índice General

### FASE 1
1. [Semana 1: Configuración del Entorno](#fase-1--semana-1-configuración-del-entorno)
2. [Semana 2: Conexión y Autenticación con Jira](#fase-1--semana-2-conexión-y-autenticación-con-jira)
3. [Semana 3: Endpoints y JQL](#fase-1--semana-3-implementación-de-endpoints-y-jql)
4. [Semana 4: Seguridad y Testing](#fase-1--semana-4-seguridad-y-testing)

### FASE 2
5. [Semana 1: Integración con Base de Datos](#fase-2--semana-1-integración-con-base-de-datos)
6. [Semana 2: Cálculo e Implementación de KPIs](#fase-2--semana-2-cálculo-e-implementación-de-kpis)
7. [Semana 3: Endpoints para Frontend](#fase-2--semana-3-endpoints-para-frontend)
8. [Semana 4: Pruebas y Optimización](#fase-2--semana-4-pruebas-y-optimización)

---

# FASE 1

---

## FASE 1 — Semana 1: Configuración del Entorno

### ✅ Instalación de Herramientas

El proyecto utiliza las siguientes herramientas base:
- **Python 3.12** como lenguaje de backend.
- **FastAPI** como framework web asíncrono.
- **PostgreSQL 15** como base de datos relacional.
- **Node.js 18 + React + Vite** para el frontend.
- **Docker Compose** para el despliegue multi-contenedor.

Las dependencias de Python se instalan con:
```bash
pip install -r requirements.txt
```

### ✅ Configuración del Proyecto (Framework Backend — FastAPI)

El punto de entrada de la aplicación es:

📂 **`app/main.py`**

Este archivo:
1. Crea la instancia de FastAPI con documentación Swagger protegida por contraseña.
2. Configura CORS para permitir peticiones del frontend (`http://localhost:5173`).
3. Registra todos los routers de la API bajo el prefijo `/api`.
4. Ejecuta auto-migraciones de esquema de base de datos al arrancar (`startup_event`).

```python
# Ejemplo del punto de entrada principal
app = FastAPI(title="MCHAV Analytics API", docs_url=None)  # docs_url=None desactiva la ruta por defecto
app.include_router(api_router, prefix="/api")               # Monta toda la API bajo /api
```

### ✅ Estructura de Carpetas y Organización del Código

El proyecto sigue el patrón **Clean Architecture** con la siguiente estructura:

```text
Mchav-Backend/
├── app/
│   ├── main.py                          # Punto de entrada de la aplicación FastAPI
│   ├── core/                            # ⚙️ CAPA DE INFRAESTRUCTURA
│   │   ├── config.py                    #   → Carga de variables de entorno (.env)
│   │   ├── database.py                  #   → Conexión a PostgreSQL con SQLAlchemy
│   │   ├── security.py                  #   → Firma/verificación HMAC SHA-256 de sesiones
│   │   ├── cache.py                     #   → Caché en memoria con TTL de 60 segundos
│   │   └── jql_config.py               #   → Consultas JQL parametrizadas para Jira
│   ├── datasources/                     # 🔌 CAPA DE FUENTES DE DATOS EXTERNAS
│   │   └── jira_datasource.py           #   → Cliente HTTP de bajo nivel para la API REST de Jira
│   ├── models/                          # 🗄️ CAPA DE MODELOS ORM (SQLAlchemy)
│   │   ├── __init__.py                  #   → Fachada que exporta todos los modelos
│   │   ├── auth.py                      #   → Modelos User y Role
│   │   ├── jira.py                      #   → Modelos Proyecto, Sprint, Issue, Transición, MapeoEstado
│   │   └── metrics.py                   #   → Modelos KpisHistoricos y LogsSincronizacion
│   ├── schemas/                         # 📄 CAPA DE ESQUEMAS DTO (Pydantic)
│   │   ├── auth_schema.py               #   → DTOs de autenticación y perfil de usuario
│   │   ├── jql.py                       #   → DTOs para consultas JQL y respuestas
│   │   └── project_schema.py            #   → DTOs de proyectos y mapeos de estado
│   ├── repositories/                    # 📦 CAPA DE ACCESO A DATOS (Patrón Repository/DAO)
│   │   ├── base.py                      #   → Repositorio genérico CRUD (Create, Read, Update, Delete)
│   │   ├── auth_repo.py                 #   → Repositorio de usuarios y roles
│   │   ├── jira_repo.py                 #   → Repositorio de proyectos, sprints, issues, transiciones
│   │   └── metrics_repo.py             #   → Repositorio de KPIs y logs de sincronización
│   ├── services/                        # 🧠 CAPA DE LÓGICA DE NEGOCIO
│   │   ├── auth_service.py              #   → Flujo OAuth 2.0 y verificación de credenciales
│   │   ├── jira_sync_service.py         #   → Motor ETL completo de sincronización con Jira
│   │   ├── jira_sync.py                 #   → Wrapper delegador al motor ETL
│   │   └── kpi.py                       #   → Cálculo de Velocity, Throughput, Lead/Cycle Time
│   └── api/v1/                          # 🎮 CAPA DE CONTROLADORES HTTP
│       ├── api.py                       #   → Router maestro que agrega todos los sub-routers
│       ├── deps.py                      #   → Inyección de dependencias (sesión + usuario)
│       └── controllers/                 #   → Controladores HTTP delgados
│           ├── auth_controller.py       #       → Login, callback OAuth, perfil, API Token
│           ├── jira_controller.py       #       → Métricas JQL, sincronización ETL, webhooks
│           └── projects_controller.py   #       → Proyectos, sprints, KPIs, mapeos de estado
├── tests/                               # 🧪 SUITE DE PRUEBAS AUTOMATIZADAS
│   ├── test_security.py                 #   → Pruebas de seguridad HMAC y protección de endpoints
│   ├── test_persistence.py              #   → Pruebas CRUD de persistencia en base de datos
│   ├── test_cycle_time.py               #   → Pruebas de cálculo de Cycle Time y Lead Time
│   ├── test_kpi_endpoints.py            #   → Pruebas de endpoints REST de KPIs
│   ├── test_pagination_sorting.py       #   → Pruebas de paginación y ordenamiento
│   └── test_cache.py                    #   → Pruebas de la caché en memoria ShortLivedCache
├── alembic/                             # 🔄 MIGRACIONES DE BASE DE DATOS
│   └── env.py                           #   → Configuración dinámica vinculada al .env
├── docs/                                # 📖 DOCUMENTACIÓN TÉCNICA DEL PROYECTO
├── seed_prueba_asd.py                   # 🌱 Script de datos de prueba en base de datos local
├── populate_jira_cloud_asd.py           # ☁️ Script de datos de prueba en Jira Cloud real
└── requirements.txt                     # 📋 Dependencias de Python
```

### ✅ Configuración de Base de Datos (PostgreSQL + SQLAlchemy)

📂 **`app/core/database.py`**

Este archivo configura la conexión a la base de datos usando SQLAlchemy:

- **`engine`**: Motor de conexión a PostgreSQL creado con la URL del `.env`.
- **`SessionLocal`**: Fábrica de sesiones que genera conexiones individuales para cada petición HTTP.
- **`Base`**: Clase base declarativa de la que heredan todos los modelos ORM.
- **`get_db()`**: Generador que inyecta una sesión de BD en cada endpoint y la cierra automáticamente al terminar.

📂 **`app/core/config.py`**

Este archivo carga **todas** las variables del archivo `.env` usando `python-dotenv`:

| Variable | Propósito |
|:---|:---|
| `DATABASE_URL` | Cadena de conexión a PostgreSQL |
| `FRONTEND_URL` | URL del frontend para CORS |
| `SESSION_SECRET_KEY` | Clave secreta para firmar cookies HMAC |
| `CLIENT_ID` / `CLIENT_SECRET` | Credenciales OAuth 2.0 de Atlassian |
| `JIRA_DOMAIN` / `JIRA_EMAIL` / `JIRA_API_TOKEN` | Credenciales de API Token directo |
| `DOCS_USER` / `DOCS_PASSWORD` | Contraseña para proteger Swagger `/docs` |

### ✅ Primera Conexión de Prueba con Jira API

📂 **`app/datasources/jira_datasource.py`**

Este archivo contiene la clase `JiraDatasource` que encapsula todas las peticiones HTTP de bajo nivel hacia la API REST v3 de Atlassian Jira. El método `get_auth_credentials()` determina automáticamente si usar API Token (Basic Auth) u OAuth 2.0 (Bearer Token).

---

## FASE 1 — Semana 2: Conexión y Autenticación con Jira

### ✅ Obtener Credenciales de Jira (OAuth 2.0)

En lugar de una autenticación simple, implementamos **OAuth 2.0 (3-Legged OAuth)** con Atlassian, que es el estándar de la industria para aplicaciones de terceros.

📂 **`app/services/auth_service.py`** — Servicio de Autenticación

El flujo OAuth 2.0 funciona así:

```text
1. Usuario hace clic en "Iniciar Sesión con Jira"
         │
         ▼
2. Backend genera un token CSRF único (state) y redirige a Atlassian
   → URL: https://auth.atlassian.com/authorize?client_id=...&state=...
         │
         ▼
3. Usuario autoriza la app en la pantalla de Atlassian
         │
         ▼
4. Atlassian redirige al callback del backend con un código temporal
   → GET /api/auth/callback?code=ABC123&state=XYZ
         │
         ▼
5. Backend intercambia el código por un access_token y refresh_token
   → POST https://auth.atlassian.com/oauth/token
         │
         ▼
6. Backend obtiene el cloud_id y el perfil del usuario (/rest/api/3/myself)
         │
         ▼
7. Backend crea o actualiza el usuario en la BD y establece una cookie firmada HMAC
```

**Funciones clave del archivo:**
- `generate_oauth_state()` → Genera un token CSRF único para prevenir ataques.
- `validate_oauth_state(state)` → Valida y consume el token CSRF.
- `build_jira_oauth_url(state)` → Construye la URL de redirección a Atlassian.
- `exchange_code_for_user_profile(code)` → Intercambia el código temporal por tokens de acceso.
- `_fetch_user_profile_with_fallback(...)` → Obtiene el perfil del usuario con 3 reintentos y fallback a API Token si hay Rate Limit (HTTP 429).

### ✅ Implementar Autenticación con Jira API

📂 **`app/api/v1/controllers/auth_controller.py`** — Controlador de Autenticación

Este controlador expone los endpoints HTTP del flujo de autenticación:

| Endpoint | Método | Descripción |
|:---|:---|:---|
| `/api/auth/login` | GET | Redirige al usuario a la pantalla OAuth de Atlassian |
| `/api/auth/callback` | GET | Recibe el código de Atlassian, crea sesión y redirige al dashboard |
| `/api/auth/me` | GET | Devuelve la información del usuario autenticado |
| `/api/auth/jira-credentials` | GET | Obtiene el estado de vinculación del API Token |
| `/api/auth/jira-credentials` | POST | Guarda y verifica un API Token personal de Jira |

### ✅ Servicio de Conexión Reutilizable (`httpx` Async)

📂 **`app/datasources/jira_datasource.py`** — Fuente de Datos de Jira

La clase `JiraDatasource` centraliza **todas** las peticiones HTTP al API de Jira:

| Método | Descripción |
|:---|:---|
| `get_auth_credentials(db, user)` | Decide automáticamente entre API Token o OAuth Bearer |
| `fetch_projects(client, base_url, headers)` | Obtiene la lista de proyectos visibles |
| `fetch_issues_jql(client, ..., jql)` | Ejecuta una consulta JQL con soporte para la migración Atlassian Change 2046 |
| `fetch_issue_changelog(client, ..., issue_id)` | Obtiene el historial de transiciones de un ticket |
| `fetch_boards_for_project(client, ..., project_key)` | Busca tableros asociados a un proyecto |
| `fetch_board_sprints(client, ..., board_id)` | Obtiene todos los sprints (activos, futuros y cerrados) |

### ✅ Manejo de Errores y Excepciones

El manejo de errores se implementa en tres niveles:

1. **Nivel HTTP (Controladores):** Uso de `HTTPException` de FastAPI con códigos de estado claros (401, 400, 500).
2. **Nivel Servicio (auth_service.py):** Reintentos con pausa exponencial ante Rate Limit 429 y fallback automático a API Token.
3. **Nivel ETL (jira_sync_service.py):** Bloques `try/except` con `db.rollback()` que evitan que una transacción fallida bloquee toda la sesión.

---

## FASE 1 — Semana 3: Implementación de Endpoints y JQL

### ✅ Escribir Queries JQL para Métricas

📂 **`app/core/jql_config.py`** — Configuración Centralizada de Consultas JQL

Este archivo define un contrato de consultas JQL parametrizadas:

```python
class JQLQueries:
    # Extrae tickets modificados en las últimas 24 horas
    DELTA_EXTRACTION = "project = '{project_key}' AND updated >= '-24h'"
    
    # Extrae tickets completados en un sprint específico
    VELOCITY_THROUGHPUT = "project = '{project_key}' AND status = '{status_done}' AND sprint = {sprint_id}"
    
    # Extrae tickets resueltos en un rango de fechas
    TIME_CYCLES = "project = '{project_key}' AND resolutiondate >= '{start_date}' AND resolutiondate <= '{end_date}'"
```

Cada consulta usa placeholders (`{project_key}`, `{sprint_id}`) que se sustituyen dinámicamente en tiempo de ejecución.

### ✅ Crear Endpoints GET/POST para Datos de Jira

📂 **`app/api/v1/endpoints/jql_queries.py`** — Endpoints de Consultas JQL

Este archivo expone endpoints que ejecutan las consultas JQL directamente contra el API de Jira y devuelven los resultados en formato JSON.

📂 **`app/api/v1/controllers/jira_controller.py`** — Controlador de Métricas Jira

Los endpoints principales son:

| Endpoint | Método | Descripción |
|:---|:---|:---|
| `/api/jira/metrics` | GET | Métricas rápidas (proyectos activos, tickets completados, en progreso, bugs críticos) |
| `/api/jira/sync` | POST | Dispara el motor ETL de sincronización en segundo plano |
| `/api/jira/sync/logs` | GET | Historial de auditoría de sincronizaciones |
| `/api/jira/webhook` | POST | Receptor de webhooks en tiempo real desde Jira |

### ✅ Mapear Respuestas JSON de Jira a Modelos

📂 **`app/schemas/jql.py`** — Esquemas DTO para JQL

Los esquemas Pydantic validan estrictamente las respuestas JSON de Jira, asegurando que los datos cumplen con el formato esperado antes de procesarlos.

📂 **`app/schemas/auth_schema.py`** — Esquemas DTO de Autenticación

Define los modelos `UserResponse`, `JiraCredentialsPayload` y `JiraCredentialsResponse` que validan las peticiones y respuestas del flujo de autenticación.

### ✅ Documentar API con Swagger/OpenAPI

📂 **`app/main.py`** (Líneas 15-46)

La documentación Swagger está **protegida por HTTP Basic Auth**:

```python
# Se desactiva la ruta /docs por defecto
app = FastAPI(docs_url=None, redoc_url=None, openapi_url=None)

# Se crea una ruta personalizada /docs que requiere usuario y contraseña
@app.get("/docs")
async def get_documentation(username: str = Depends(get_current_username)):
    return get_swagger_ui_html(openapi_url="/openapi.json", title="MCHAV Analytics API Docs")
```

Para acceder: `http://localhost:8000/docs` → Se pide usuario y contraseña definidos en el `.env` (`DOCS_USER` / `DOCS_PASSWORD`).

---

## FASE 1 — Semana 4: Seguridad y Testing

### ✅ Implementar Autenticación HMAC SHA-256

📂 **`app/core/security.py`** — Módulo de Seguridad Criptográfica

En lugar de JWT (que requiere almacenar tokens en el frontend), implementamos **HMAC SHA-256** para firmar las cookies de sesión. Esto es más seguro para nuestra arquitectura porque:

1. Las cookies son `HTTP-Only` → JavaScript del navegador NO puede leerlas (previene XSS).
2. Las cookies tienen `SameSite=Lax` → El navegador NO las envía en peticiones cross-origin (previene CSRF).
3. La firma HMAC garantiza que nadie puede falsificar un ID de usuario.

**Funciones del archivo:**

```python
def sign_session_id(user_id: int) -> str:
    # Toma un user_id (ej: 5) y genera "5.abc123hash..."
    # La firma se calcula con HMAC-SHA256 usando SESSION_SECRET_KEY

def verify_session_id(signed_value: str) -> int | None:
    # Toma "5.abc123hash...", separa el ID y la firma,
    # recalcula la firma esperada y compara en tiempo constante (hmac.compare_digest)
    # Si coincide, devuelve 5. Si no, devuelve None.
```

### ✅ Proteger Endpoints con Inyección de Dependencias

📂 **`app/api/v1/deps.py`** — Dependencias de Inyección

En lugar de un middleware global, usamos el sistema de **Dependency Injection** de FastAPI:

```python
def get_current_user_id(request: Request) -> int:
    # 1. Extrae la cookie "session_id" del request
    # 2. Verifica la firma HMAC
    # 3. Si es inválida, lanza HTTP 401
    # 4. Si es válida, devuelve el user_id

def check_user_exists(db: Session, user_id: int):
    # Verifica que el user_id existe en la base de datos
```

Cada endpoint protegido inyecta estas funciones:
```python
@router.get("/metrics")
async def get_metrics(request: Request, db: Session = Depends(get_db)):
    user_id = get_current_user_id(request)  # ← Verifica la sesión
    user = check_user_exists(db, user_id)   # ← Verifica el usuario en BD
    ...
```

### ✅ Pruebas Unitarias y de Integración

📂 **`tests/`** — Suite Completa de Pruebas Automatizadas

| Archivo de Tests | Qué Valida | Cantidad |
|:---|:---|:---|
| `test_security.py` | Firma/verificación HMAC, protección de endpoints sin cookie, endpoints con sesión válida | 7 tests |
| `test_persistence.py` | Operaciones CRUD completas sobre la base de datos (crear, leer, actualizar, eliminar) | 2 tests |
| `test_cycle_time.py` | Cálculos de Cycle Time, Lead Time con datos ficticios y edge cases | 8 tests |
| `test_kpi_endpoints.py` | Endpoints REST de KPIs, mapeos de estado y logs de sincronización | 4 tests |
| `test_pagination_sorting.py` | Paginación (`limit`, `offset`) y ordenamiento (`sort`, `order`) en todos los endpoints | 4 tests |
| `test_cache.py` | Caché en memoria ShortLivedCache (hit, miss, TTL expirado) | 3 tests |
| **TOTAL** | | **28 tests** |

Para ejecutar todas las pruebas:
```bash
pytest
# Resultado esperado: 28 passed in 2.30s
```

---

# FASE 2

---

## FASE 2 — Semana 1: Integración con Base de Datos

### ✅ Diseñar e Implementar Modelos de Datos

Los modelos ORM están separados por dominio en 3 archivos:

📂 **`app/models/auth.py`** — Modelos de Autenticación

| Modelo | Tabla | Descripción |
|:---|:---|:---|
| `Role` | `roles` | Control de acceso basado en roles (Administrador, Analista, Líder) |
| `User` | `usuarios` | Usuarios del sistema con credenciales OAuth y API Token de Jira |

Campos clave de `User`:
- `jira_account_id`: ID único del usuario en Atlassian
- `access_token` / `refresh_token`: Tokens OAuth 2.0
- `cloud_id`: Identificador del workspace de Jira
- `jira_domain` / `jira_email` / `jira_api_token`: Credenciales de API Token directo

📂 **`app/models/jira.py`** — Modelos del Dominio de Jira

| Modelo | Tabla | Descripción |
|:---|:---|:---|
| `Proyecto` | `proyectos` | Proyectos sincronizados desde Jira (`key_proyecto`, `nombre`, `id_board`) |
| `Sprint` | `sprints` | Sprints Agile con fechas de inicio, fin y completitud |
| `Issue` | `issues` | Tickets de Jira (historias, bugs, tareas) con story points |
| `TransicionEstadoIssue` | `transiciones_estado_issue` | Historial inmutable de cambios de estado de cada ticket |
| `MapeoEstado` | `mapeo_estados` | Tabla de configuración que mapea estados de Jira a categorías base (TODO, IN_PROGRESS, DONE) |
| `issues_sprints` | `issues_sprints` | Tabla intermedia N:M entre Issues y Sprints |

📂 **`app/models/metrics.py`** — Modelos de Métricas

| Modelo | Tabla | Descripción |
|:---|:---|:---|
| `KpisHistoricos` | `kpis_historicos` | KPIs calculados por proyecto y sprint (Velocity, Throughput, Lead/Cycle Time) |
| `LogsSincronizacion` | `logs_sincronizacion` | Auditoría ETL (fecha, duración, resultado, tickets procesados, errores) |

### ✅ Crear Migraciones de Base de Datos (Alembic)

📂 **`alembic/env.py`** — Configuración de Migraciones

Alembic está configurado para leer la `DATABASE_URL` directamente del `.env`. Para ejecutar migraciones:

```bash
alembic upgrade head   # Aplica todas las migraciones pendientes
alembic revision --autogenerate -m "descripcion"   # Genera nueva migración
```

Además, el `startup_event` en `main.py` ejecuta auto-migraciones de esquema al arrancar para agregar columnas faltantes (como `id_board`).

### ✅ Implementar Repositorios/DAOs

📂 **`app/repositories/base.py`** — Repositorio Genérico CRUD

Es una clase genérica que proporciona operaciones CRUD estándar a **todos** los modelos:

```python
class CRUDBase(Generic[ModelType]):
    def get(db, id)           # Buscar por ID primario
    def get_multi(db, ...)    # Listar con paginación (skip, limit) y ordenamiento (sort, order)
    def create(db, obj_in)    # Crear un nuevo registro
    def update(db, db_obj, obj_in)  # Actualizar un registro existente
    def remove(db, id)        # Eliminar un registro
```

Los repositorios específicos **heredan** de `CRUDBase` y agregan métodos especializados:

| Repositorio | Archivo | Métodos Especializados |
|:---|:---|:---|
| `CRUDUser` | `auth_repo.py` | `get_by_jira_account_id()` |
| `CRUDProyecto` | `jira_repo.py` | `get_by_key()` |
| `CRUDSprint` | `jira_repo.py` | `get_by_project()`, `get_by_id_sprint()` |
| `CRUDIssue` | `jira_repo.py` | `get_by_key()`, `get_resolved_stats_by_project()`, `get_resolved_stats_by_sprint()` |
| `CRUDTransicion` | `jira_repo.py` | `get_existing()`, `delete_by_issue()` |
| `CRUDMapeoEstado` | `jira_repo.py` | `get_by_project_and_base()`, `delete_by_project()` |
| `CRUDKpi` | `metrics_repo.py` | `get_general_kpi()`, `get_sprint_kpi()`, `get_all_by_project()` |
| `CRUDLog` | `metrics_repo.py` | `get_recent()` |

📂 **`app/repositories/__init__.py`** — Fachada de Repositorios

Exporta instancias singleton de cada repositorio para poder usarlos con una sola importación:
```python
from app.repositories import user_repo, project_repo, sprint_repo, issue_repo, kpi_repo, log_repo
```

### ✅ Pruebas de Persistencia

📂 **`tests/test_persistence.py`**

Valida el ciclo CRUD completo (Crear → Leer → Actualizar → Eliminar) sobre la base de datos usando SQLite en memoria para evitar afectar la BD de producción.

---

## FASE 2 — Semana 2: Cálculo e Implementación de KPIs

### ✅ Definir Fórmulas y Lógica de Cada KPI

📂 **`app/services/kpi.py`** — Motor de Cálculo de KPIs

Este es el archivo más importante para las métricas. Contiene dos funciones principales:

**1. `get_issue_cycle_time_days(issue, in_progress_statuses)`**

Calcula el **Cycle Time** de un ticket individual:

```text
Cycle Time = Fecha de Resolución - Primera Fecha en que el ticket entró a "In Progress"

Si no hay transición a "In Progress", se usa:
Cycle Time = Fecha de Resolución - Fecha de Creación (esto sería Lead Time)
```

**2. `calculate_and_save_kpis(db, proyecto_id)`**

Calcula y persiste los KPIs de un proyecto completo:

| KPI | Fórmula | Campo en BD |
|:---|:---|:---|
| **Velocity** | Suma de Story Points de tickets resueltos | `velocity_total_sp` |
| **Velocity Promedio** | Promedio de Velocity de todos los sprints cerrados | `velocity_promedio_historico` |
| **Throughput** | Cantidad total de tickets resueltos | `throughput_issues` |
| **Lead Time** | Promedio de (resolved_at - created_at) en días | `lead_time_promedio_dias` |
| **Cycle Time** | Promedio de (resolved_at - primera_transición_in_progress) en días | `cycle_time_promedio_dias` |

Los cálculos se delegan al motor SQL de PostgreSQL (no a Python) para máximo rendimiento.

### ✅ Motor ETL Completo de Sincronización

📂 **`app/services/jira_sync_service.py`** — Motor ETL

Este archivo orquesta todo el proceso de extracción, transformación y carga:

```text
1. sync_projects()         → Descarga proyectos de Jira y los inserta/actualiza en BD
2. sync_issues_for_project() → Para cada proyecto:
   a. Busca tableros y descarga TODOS los sprints (activos, futuros, cerrados)
   b. Filtra tableros estrictamente por projectKey (evita fuga entre proyectos)
   c. Descarga tickets vía JQL con expansión de changelog (expand=changelog)
   d. Extrae y registra transiciones de estado de cada ticket
   e. Crea sprints automáticos de respaldo si no existen en BD (protección FK)
3. calculate_and_save_kpis() → Calcula KPIs globales y por sprint
```

**Decisiones técnicas clave:**
- La sincronización corre en un `BackgroundTask` de FastAPI para no bloquear la interfaz.
- Abre su propia sesión `SessionLocal()` independiente para evitar errores de sesión cerrada.
- Implementa `db.rollback()` ante excepciones para evitar `PendingRollbackError`.
- Cumple con la migración Atlassian Change 2046 usando `/search/jql` con fallback a `/search`.

### ✅ Pruebas de Cálculo de KPIs

📂 **`tests/test_cycle_time.py`** — 8 Pruebas de Cycle Time

Valida los cálculos de Cycle Time con múltiples escenarios:
- Ticket con transición normal (To Do → In Progress → Done)
- Ticket sin transiciones (usa Lead Time como fallback)
- Ticket no resuelto (retorna 0.0)
- Ticket con múltiples transiciones (usa la primera entrada a In Progress)
- Sprint con múltiples tickets (promedio correcto)

---

## FASE 2 — Semana 3: Endpoints para Frontend

### ✅ Endpoints GET para KPIs Calculados

📂 **`app/api/v1/controllers/projects_controller.py`** — Controlador de Proyectos

| Endpoint | Método | Descripción |
|:---|:---|:---|
| `/api/projects` | GET | Lista todos los proyectos sincronizados con paginación |
| `/api/projects/{id}/kpis` | GET | KPIs calculados de un proyecto, filtrable por sprint |
| `/api/projects/{id}/sprints` | GET | Sprints de un proyecto con paginación y ordenamiento |
| `/api/projects/{id}/statuses` | GET | Estados únicos encontrados en los tickets del proyecto |
| `/api/projects/{id}/mappings` | GET | Mapeo de estados configurado (Jira → TODO/IN_PROGRESS/DONE) |
| `/api/projects/{id}/mappings` | POST | Guardar nuevo mapeo y recalcular KPIs automáticamente |

### ✅ Paginación y Ordenamiento

📂 **`app/repositories/base.py`** — Método `get_multi()`

Todos los endpoints de listado soportan los siguientes parámetros:

| Parámetro | Tipo | Descripción |
|:---|:---|:---|
| `limit` | int | Máximo de resultados a devolver (default: 100) |
| `offset` | int | Cantidad de registros a saltar (default: 0) |
| `sort` | str | Campo por el cual ordenar (ej: `fecha_inicio`, `id_proyecto`) |
| `order` | str | Dirección del ordenamiento: `asc` o `desc` |

### ✅ Optimización de Queries SQL

📂 **`app/repositories/jira_repo.py`** — Métodos `get_resolved_stats_by_project()` y `get_resolved_stats_by_sprint()`

Los cálculos de KPIs se delegan **completamente al motor SQL** de PostgreSQL:

```python
# Se calcula TODO en una sola consulta SQL, no en Python:
return db.query(
    func.sum(Issue.story_points),           # Velocity (Story Points totales)
    func.count(Issue.id_jira),              # Throughput (cantidad de tickets)
    func.avg(lead_time_expression),         # Lead Time promedio en días
    func.avg(cycle_time_expression)         # Cycle Time promedio en días
).filter(
    Issue.id_proyecto == project_id,
    Issue.resolved_at.isnot(None)           # Solo tickets resueltos
).first()
```

Esto es **significativamente más rápido** que cargar todos los tickets en memoria y calcular en Python.

---

## FASE 2 — Semana 4: Pruebas y Optimización

### ✅ Caché en Memoria ShortLivedCache

📂 **`app/core/cache.py`** — Caché Segura de Corto Ciclo

La caché almacena métricas JQL por 60 segundos por usuario, evitando consultas repetidas a la API de Jira:

```python
class ShortLivedCache:
    def __init__(self, ttl_seconds=60):  # Time-To-Live de 60 segundos
        self._store = {}                  # Diccionario en memoria
        self._lock = threading.Lock()     # Lock para seguridad en concurrencia

    def get(key):    # Busca en caché, elimina si expiró
    def set(key, value):  # Almacena con fecha de expiración
    def clear():     # Limpia toda la caché
```

### ✅ Resumen de la Suite Completa de Pruebas

```bash
$ pytest
tests/test_cache.py ...                         # 3 passed — Caché en memoria
tests/test_cycle_time.py ........               # 8 passed — Cálculos de tiempos
tests/test_kpi_endpoints.py ....                # 4 passed — Endpoints de KPIs
tests/test_pagination_sorting.py ....           # 4 passed — Paginación y ordenamiento
tests/test_persistence.py ..                    # 2 passed — CRUD en base de datos
tests/test_security.py .......                  # 7 passed — Seguridad HMAC y protección
======================= 28 passed in 2.30s ======================
```

---

## 🎯 Conclusión

El proyecto MCHAV Analytics implementa **al 100%** todos los entregables del syllabus de Fase 1 y Fase 2, con una arquitectura Clean Architecture robusta, suite de pruebas automatizadas con 28 tests y documentación técnica completa.
